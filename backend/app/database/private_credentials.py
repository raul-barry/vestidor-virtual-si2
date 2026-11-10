"""Create and safely reuse private, per-account seed credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import tempfile
from typing import Any


DEFAULT_CREDENTIALS_DIR = Path(__file__).resolve().parents[2] / "private_credentials"


class CredentialManifestError(ValueError):
    """The private login manifest is missing, unsafe, or inconsistent."""


def _validate_location(path: Path) -> Path:
    resolved_dir = DEFAULT_CREDENTIALS_DIR.resolve()
    if path.is_symlink():
        raise CredentialManifestError("No se admite un enlace simbólico para credenciales.")
    resolved = path.resolve()
    if not resolved.is_relative_to(resolved_dir):
        raise CredentialManifestError(
            "El archivo de credenciales debe guardarse en backend/private_credentials/."
        )
    return resolved


def _identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(field) or "") for field in (
        "name", "email", "role", "tenant", "branch",
    ))


def _write_private(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if exclusive:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(path, 0o600)
        return

    fd, temporary_name = tempfile.mkstemp(prefix=".credentials-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_credentials(
    path: Path,
    identities: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Load an existing matching manifest or create unique pending passwords.

    Passwords are returned only to the caller in memory. Callers must never
    include this returned object in logs, CLI reports, or API responses.
    """
    target = _validate_location(path)
    expected = sorted((_identity_key(row) for row in identities))
    if len(expected) != len(set(expected)):
        raise CredentialManifestError("La lista de cuentas contiene identidades duplicadas.")

    if target.exists():
        try:
            manifest = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CredentialManifestError("No se pudo leer el archivo privado de credenciales.") from exc
        entries = manifest.get("accounts") if isinstance(manifest, dict) else None
        if not isinstance(entries, list) or sorted(_identity_key(row) for row in entries) != expected:
            raise CredentialManifestError("El archivo privado no coincide con las cuentas previstas.")
        passwords = [row.get("initial_password") for row in entries]
        if any(not isinstance(password, str) or len(password) < 20 for password in passwords):
            raise CredentialManifestError("El archivo privado contiene una contraseña inválida.")
        if len(passwords) != len(set(passwords)):
            raise CredentialManifestError("Las contraseñas iniciales deben ser únicas por cuenta.")
        return manifest, False

    entries = []
    for identity in identities:
        entries.append({
            **identity,
            "initial_password": secrets.token_urlsafe(24),
            "status": "PENDIENTE_APPLY",
        })
    manifest = {"version": 1, "accounts": entries}
    try:
        _write_private(target, manifest, exclusive=True)
    except FileExistsError as exc:
        raise CredentialManifestError(
            "El archivo apareció durante la preparación; vuelve a ejecutar el preflight."
        ) from exc
    return manifest, True


def mark_credentials_active(path: Path, manifest: dict[str, Any]) -> None:
    target = _validate_location(path)
    active = {
        **manifest,
        "accounts": [
            {**account, "status": "ACTIVO"} for account in manifest["accounts"]
        ],
    }
    _write_private(target, active, exclusive=False)
