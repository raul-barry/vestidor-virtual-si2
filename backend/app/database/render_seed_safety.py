"""Narrow target and backup checks for the one approved Render database."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from sqlalchemy.engine import URL, make_url


APPROVED_RENDER_POSTGRES_ID = "dpg-dboh755g1s2s73f6ej8g-a"
APPROVED_RENDER_DATABASE_NAME = "vestidor_db"
APPROVED_RENDER_POSTGRES_MAJOR = 16
BACKUP_MAX_AGE = timedelta(hours=24)


class RenderSeedSafetyError(ValueError):
    """A Render target or backup did not meet the explicit safety checks."""


def validate_render_url(database_url: str | URL, postgres_id: str) -> dict[str, str]:
    """Validate a DSN against the one Render Postgres ID without returning secrets."""
    if postgres_id != APPROVED_RENDER_POSTGRES_ID:
        raise RenderSeedSafetyError("El ID de Postgres no está en la lista permitida.")
    url = make_url(database_url) if isinstance(database_url, str) else database_url
    if url.get_backend_name() != "postgresql":
        raise RenderSeedSafetyError("El destino Render debe usar PostgreSQL.")
    host = (url.host or "").lower().rstrip(".")
    expected_host = APPROVED_RENDER_POSTGRES_ID.lower()
    internal_host = host == expected_host
    external_host = host.startswith(expected_host + ".") and host.endswith(".render.com")
    if not (internal_host or external_host):
        raise RenderSeedSafetyError("El host configurado no corresponde al Postgres autorizado.")
    if url.database != APPROVED_RENDER_DATABASE_NAME:
        raise RenderSeedSafetyError("El nombre de base no coincide con el destino autorizado.")
    if url.port not in (None, 5432):
        raise RenderSeedSafetyError("El puerto configurado no corresponde a PostgreSQL de Render.")
    if external_host and url.query.get("sslmode", "require") != "require":
        raise RenderSeedSafetyError("Las conexiones externas requieren sslmode=require.")
    return {
        "postgres_id": APPROVED_RENDER_POSTGRES_ID,
        "database_name": APPROVED_RENDER_DATABASE_NAME,
        "connection_kind": "internal" if internal_host else "external",
    }


def probe_render_connection(connection, postgres_id: str) -> dict[str, str]:
    """Verify the live database identity/version through an existing connection."""
    if postgres_id != APPROVED_RENDER_POSTGRES_ID:
        raise RenderSeedSafetyError("El ID de Postgres no está en la lista permitida.")
    row = connection.exec_driver_sql(
        "SELECT current_database(), current_setting('server_version_num')"
    ).one()
    database_name, version_num = str(row[0]), str(row[1])
    if database_name != APPROVED_RENDER_DATABASE_NAME:
        raise RenderSeedSafetyError("La conexión terminó en una base distinta de la autorizada.")
    if not version_num.startswith(f"{APPROVED_RENDER_POSTGRES_MAJOR}"):
        raise RenderSeedSafetyError("La versión de PostgreSQL no coincide con el recurso verificado.")
    return {"postgres_id": postgres_id, "database_name": database_name,
            "postgres_major": str(APPROVED_RENDER_POSTGRES_MAJOR)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_custom_dump(path: Path, *, pg_restore: str | None = None) -> str:
    """Read the archive table of contents without restoring or modifying data."""
    executable = pg_restore or shutil.which("pg_restore")
    if not executable:
        raise RenderSeedSafetyError("No se encontró pg_restore para validar el respaldo.")
    if not path.is_file() or path.stat().st_size <= 0:
        raise RenderSeedSafetyError("El archivo de respaldo no existe o está vacío.")
    result = subprocess.run(
        [executable, "--list", str(path)], capture_output=True, text=True,
        check=False, timeout=120,
    )
    if result.returncode != 0:
        raise RenderSeedSafetyError("pg_restore no pudo leer el archivo de respaldo.")
    listing = result.stdout
    if f"; Database: {APPROVED_RENDER_DATABASE_NAME}" not in listing:
        raise RenderSeedSafetyError("El respaldo no declara la base Render esperada.")
    return _sha256(path)


def verify_backup_attestation(
    backup_file: Path,
    manifest_file: Path,
    postgres_id: str,
    *,
    now: datetime | None = None,
    pg_restore: str | None = None,
) -> dict[str, str]:
    """Verify file integrity, archive DB name, source ID, and backup freshness."""
    if postgres_id != APPROVED_RENDER_POSTGRES_ID:
        raise RenderSeedSafetyError("El ID de Postgres no está en la lista permitida.")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(str(manifest["created_at_utc"]).replace("Z", "+00:00"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RenderSeedSafetyError("No se pudo leer el manifiesto del respaldo.") from exc
    if created.tzinfo is None:
        raise RenderSeedSafetyError("La fecha del respaldo debe incluir zona horaria UTC.")
    now = now or datetime.now(timezone.utc)
    age = now.astimezone(timezone.utc) - created.astimezone(timezone.utc)
    if age < timedelta(0) or age > BACKUP_MAX_AGE:
        raise RenderSeedSafetyError("El respaldo debe tener menos de 24 horas y no estar fechado en el futuro.")
    if manifest.get("render_postgres_id") != postgres_id:
        raise RenderSeedSafetyError("El manifiesto no identifica el Postgres autorizado.")
    if manifest.get("database_name") != APPROVED_RENDER_DATABASE_NAME:
        raise RenderSeedSafetyError("El manifiesto no identifica la base autorizada.")
    if manifest.get("file_name") != backup_file.name:
        raise RenderSeedSafetyError("El manifiesto no corresponde al archivo indicado.")
    digest = inspect_custom_dump(backup_file, pg_restore=pg_restore)
    if manifest.get("sha256") != digest:
        raise RenderSeedSafetyError("El hash del respaldo no coincide con el manifiesto.")
    return {"render_postgres_id": postgres_id,
            "database_name": APPROVED_RENDER_DATABASE_NAME,
            "created_at_utc": created.isoformat(), "sha256": digest}
