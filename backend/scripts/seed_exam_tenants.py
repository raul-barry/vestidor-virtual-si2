"""Preview/apply the synthetic tenant fixture locally or in the guarded Render DB."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.core.config import settings
from app.database.database import SessionLocal
from app.database.private_credentials import (
    CredentialManifestError,
    DEFAULT_CREDENTIALS_DIR,
    mark_credentials_active,
    prepare_credentials,
)
from app.database.render_seed_safety import (
    APPROVED_RENDER_POSTGRES_ID,
    RenderSeedSafetyError,
    probe_render_connection,
    validate_render_url,
    verify_backup_attestation,
)
from app.database.tenant_exam_seed import (
    _user_manifest,
    apply_tenant_seed,
    audit_tenant_seeded_data,
    dry_run_report,
)
from app.database.tenant_exam_seed_data import TENANTS
from app.core.security import verify_password
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.services.platform_admin_bootstrap import bootstrap_platform_admin


PLATFORM_ADMIN_EMAIL = "superadmin.saas@vestidor.com"


def _credential_identities(report: dict) -> list[dict[str, str | None]]:
    rows = []
    for user in report["user_manifest"]:
        rows.append({
            "name": str(user["name"]), "email": str(user["email"]),
            "role": str(user["role"]), "tenant": str(user["organization"]),
            "branch": user["branch"],
        })
    rows.append({
        "name": "Administrador Plataforma", "email": PLATFORM_ADMIN_EMAIL,
        "role": "ADMINISTRADOR_PLATAFORMA", "tenant": "GLOBAL", "branch": None,
    })
    return rows


def _verify_existing_credentials(db, entries: list[dict]) -> None:
    role_ids = {row.nombre: row.id_rol for row in db.scalars(select(Rol)).all()}
    for entry in entries:
        user = db.scalar(select(Usuario).where(Usuario.correo == entry["email"]))
        if user is None:
            continue
        if (user.rol.nombre != entry["role"]
                or (entry["role"] == "ADMINISTRADOR_PLATAFORMA" and user.id_organizacion is not None)
                or (entry["role"] != "ADMINISTRADOR_PLATAFORMA"
                    and user.id_organizacion is None)):
            raise CredentialManifestError(
                "Una cuenta existente no coincide con el rol o tenant esperado; no se modifica."
            )
        if not verify_password(entry["initial_password"], user.password_hash):
            raise CredentialManifestError(
                "Una cuenta existente no coincide con el manifiesto privado; no se cambia su contraseña."
            )
    platform_role_id = role_ids.get("ADMINISTRADOR_PLATAFORMA")
    if platform_role_id is not None:
        other_platform_admins = db.scalars(select(Usuario).where(
            Usuario.id_rol == platform_role_id,
            Usuario.correo != PLATFORM_ADMIN_EMAIL,
        )).all()
        if other_platform_admins:
            raise CredentialManifestError(
                "Ya existe otro superadministrador SaaS; el bootstrap no creará una segunda cuenta."
            )


def _is_local_database() -> bool:
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite":
        return True
    return (url.host or "").lower() in {"localhost", "127.0.0.1", "::1"}


def _connect_and_verify_render(db, postgres_id: str) -> dict[str, str]:
    try:
        with db.connection() as connection:
            return probe_render_connection(connection, postgres_id)
    except RenderSeedSafetyError:
        raise
    except SQLAlchemyError as exc:
        # SQLAlchemy errors can contain connection details; never echo them.
        raise RenderSeedSafetyError(
            "No se pudo verificar la conexión Render; los detalles de conexión se omitieron."
        ) from exc


def _mark_unseedable_shared_data(report: dict) -> None:
    missing = report["shared_master_data"]["missing"]
    if any(missing.values()):
        report["blockers"].append(
            "El modo Render no crea roles, categorías, tallas ni colores globales; "
            "faltan: " + json.dumps(missing, ensure_ascii=False)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preflight local de solo lectura (predeterminado).")
    mode.add_argument("--apply", action="store_true", help="Aplica solo a una base local development/test.")
    mode.add_argument("--render-dry-run", action="store_true", help="Preflight remoto de solo lectura contra el Render permitido.")
    mode.add_argument("--render-apply", action="store_true", help="Aplica fixture sintético con controles reforzados en el Render permitido.")
    parser.add_argument("--confirm-local-database", action="store_true")
    parser.add_argument("--render-postgres-id", help="ID exacto del único Postgres Render permitido.")
    parser.add_argument("--confirm-render-target", help="Repite el ID Render exacto como confirmación.")
    parser.add_argument("--confirm-render-apply", help="Debe ser APPLY:<ID Render>.")
    parser.add_argument("--backup-file", type=Path, help="pg_dump custom-format previamente generado.")
    parser.add_argument("--backup-manifest", type=Path, help="Manifiesto generado con el respaldo.")
    parser.add_argument(
        "--credentials-file", type=Path,
        default=DEFAULT_CREDENTIALS_DIR / "fashionstore-render-credentials.json",
        help="Archivo privado excluido de Git para contraseñas únicas por cuenta.",
    )
    args = parser.parse_args()

    local_apply = args.apply
    render_dry_run = args.render_dry_run
    render_apply = args.render_apply

    if local_apply:
        if settings.environment.lower() not in {"development", "test"}:
            parser.error("--apply local se bloquea en production.")
        if not _is_local_database():
            parser.error("--apply local exige SQLite o PostgreSQL localhost.")
        if not args.confirm_local_database:
            parser.error("Agrega --confirm-local-database después de revisar el destino local.")

    render_mode = render_dry_run or render_apply
    if render_mode:
        if args.render_postgres_id != APPROVED_RENDER_POSTGRES_ID:
            parser.error("--render-postgres-id no coincide con el único recurso permitido.")
        if args.confirm_render_target != APPROVED_RENDER_POSTGRES_ID:
            parser.error("--confirm-render-target debe repetir exactamente el ID permitido.")
        if settings.environment.lower() != "production":
            parser.error("El modo Render requiere ENVIRONMENT=production.")
        try:
            validate_render_url(settings.database_url, args.render_postgres_id)
        except RenderSeedSafetyError as exc:
            parser.error(str(exc))

    if render_apply:
        if args.confirm_render_apply != f"APPLY:{APPROVED_RENDER_POSTGRES_ID}":
            parser.error("--confirm-render-apply debe ser APPLY:<ID Render>.")
        if not args.backup_file or not args.backup_manifest:
            parser.error("--render-apply requiere --backup-file y --backup-manifest verificados.")
        try:
            verify_backup_attestation(
                args.backup_file.resolve(), args.backup_manifest.resolve(), args.render_postgres_id,
            )
        except RenderSeedSafetyError as exc:
            parser.error(str(exc))

    password = os.environ.get("FASHIONSTORE_SEED_PASSWORD", "") if local_apply else ""
    if local_apply and not password:
        parser.error("Define FASHIONSTORE_SEED_PASSWORD en el entorno; el valor nunca se imprime.")

    with SessionLocal() as db:
        if render_mode:
            try:
                live_target = _connect_and_verify_render(db, args.render_postgres_id)
            except RenderSeedSafetyError as exc:
                parser.error(str(exc))
            db.info["verified_render_postgres_id"] = args.render_postgres_id
            if render_apply:
                preflight = dry_run_report(db)
                _mark_unseedable_shared_data(preflight)
                if preflight["blockers"]:
                    parser.error("DRY RUN bloqueado: " + " | ".join(preflight["blockers"]))
                identities = _credential_identities(preflight)
                # Keep the original path until validation so a final-component
                # symlink cannot be hidden by Path.resolve().
                credential_path = args.credentials_file
                identity_emails = [row["email"] for row in identities]
                if not credential_path.exists():
                    existing = db.scalars(select(Usuario.correo).where(
                        Usuario.correo.in_(identity_emails),
                    )).all()
                    platform_role = db.scalar(select(Rol).where(
                        Rol.nombre == "ADMINISTRADOR_PLATAFORMA",
                    ))
                    if platform_role is not None and db.scalar(select(Usuario.id_usuario).where(
                        Usuario.id_rol == platform_role.id_rol,
                    )) is not None:
                        parser.error(
                            "Ya existe un superadministrador y no hay manifiesto privado; "
                            "no se reemplazarán credenciales."
                        )
                    if existing:
                        parser.error(
                            "Hay cuentas objetivo preexistentes sin manifiesto privado; "
                            "se detiene para no sobrescribir sus contraseñas."
                        )
                try:
                    credential_manifest, _created = prepare_credentials(
                        credential_path, identities,
                    )
                    _verify_existing_credentials(db, credential_manifest["accounts"])
                except CredentialManifestError as exc:
                    parser.error(str(exc))
                credentials = {
                    item["email"]: item["initial_password"]
                    for item in credential_manifest["accounts"]
                }
                tenant_emails = {
                    str(row["email"])
                    for spec in TENANTS for row in _user_manifest(spec)
                }
                report = apply_tenant_seed(
                    db, {email: credentials[email] for email in tenant_emails},
                    allow_render_production=True, seed_shared_master_data=False,
                )
                db.info.pop("organization_id", None)
                platform_user, platform_created = bootstrap_platform_admin(
                    db, PLATFORM_ADMIN_EMAIL, credentials[PLATFORM_ADMIN_EMAIL],
                )
                db.commit()
                mark_credentials_active(credential_path, credential_manifest)
                report["platform_administrator"] = {
                    "email": platform_user.correo,
                    "organization_id": platform_user.id_organizacion,
                    "role": platform_user.rol.nombre,
                    "created": platform_created,
                }
                report["credentials"] = {
                    "file": str(credential_path.resolve()),
                    "accounts": len(credential_manifest["accounts"]),
                    "passwords_unique": True,
                    "values_logged": False,
                }
            else:
                report = dry_run_report(db)
                _mark_unseedable_shared_data(report)
                audit = audit_tenant_seeded_data(db)
                report["current_tenant_audit"] = audit
                if audit["blockers"]:
                    report["blockers"].extend(audit["blockers"])
            report["verified_target"] = live_target
        elif local_apply:
            report = apply_tenant_seed(db, password)
        else:
            report = dry_run_report(db)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not report.get("blockers") else 2


if __name__ == "__main__":
    sys.exit(main())
