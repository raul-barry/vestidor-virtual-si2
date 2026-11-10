"""Create and attest a custom-format pg_dump from the single approved Render DB."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.database.render_seed_safety import (
    APPROVED_RENDER_DATABASE_NAME,
    APPROVED_RENDER_POSTGRES_ID,
    RenderSeedSafetyError,
    inspect_custom_dump,
    probe_render_connection,
    validate_render_url,
)


def create_backup(output_file: Path, postgres_id: str) -> dict[str, str]:
    if settings.environment.lower() != "production":
        raise RenderSeedSafetyError("El respaldo Render solo se crea desde configuración production.")
    url = make_url(settings.database_url)
    target = validate_render_url(url, postgres_id)
    if output_file.exists():
        raise RenderSeedSafetyError("El archivo indicado ya existe; no se sobrescribe.")
    manifest_file = output_file.with_suffix(output_file.suffix + ".manifest.json")
    if manifest_file.exists():
        raise RenderSeedSafetyError("El manifiesto indicado ya existe; no se sobrescribe.")
    executable = shutil.which("pg_dump")
    if not executable:
        raise RenderSeedSafetyError("No se encontró pg_dump; instale los PostgreSQL client tools.")

    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as connection:
            live = probe_render_connection(connection, postgres_id)
        if live["database_name"] != target["database_name"]:
            raise RenderSeedSafetyError("La conexión no coincide con el recurso Render aprobado.")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        if url.password is not None:
            environment["PGPASSWORD"] = url.password
        environment["PGHOST"] = url.host or ""
        environment["PGPORT"] = str(url.port or 5432)
        environment["PGUSER"] = url.username or ""
        environment["PGDATABASE"] = APPROVED_RENDER_DATABASE_NAME
        environment["PGSSLMODE"] = str(url.query.get("sslmode", "require"))
        environment["PGCONNECT_TIMEOUT"] = "10"
        command = [
            executable, "--no-password", "--format=custom", "--no-owner", "--no-acl",
            "--file", str(output_file),
        ]
        result = subprocess.run(command, env=environment, capture_output=True,
                                check=False, timeout=1800)
        if result.returncode != 0:
            output_file.unlink(missing_ok=True)
            raise RenderSeedSafetyError("pg_dump falló; no se generó manifiesto de respaldo.")

        digest = inspect_custom_dump(output_file)
        manifest = {
            "render_postgres_id": postgres_id,
            "database_name": APPROVED_RENDER_DATABASE_NAME,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "file_name": output_file.name,
            "sha256": digest,
            "format": "custom",
            "server_major": live["postgres_major"],
        }
        with manifest_file.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return {"backup_file": output_file.name,
                "manifest_file": manifest_file.name,
                "database_name": manifest["database_name"],
                "render_postgres_id": postgres_id,
                "sha256": digest,
                "created_at_utc": manifest["created_at_utc"]}
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Ruta absoluta para el archivo .dump.")
    parser.add_argument("--render-postgres-id", required=True)
    parser.add_argument("--confirm-render-target", required=True,
                        help="Repite exactamente el ID Render aprobado.")
    args = parser.parse_args()
    if args.confirm_render_target != args.render_postgres_id:
        parser.error("La confirmación debe repetir exactamente --render-postgres-id.")
    try:
        report = create_backup(args.output.resolve(), args.render_postgres_id)
    except RenderSeedSafetyError as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
