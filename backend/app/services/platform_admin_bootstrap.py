import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.seed import seed_roles
from app.models.rol import Rol
from app.models.usuario import Usuario


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def bootstrap_platform_admin(db: Session, email: str, password: str) -> tuple[Usuario, bool]:
    """Create the first global platform admin; repeated calls never change credentials."""
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("Provide a valid administrator email address")
    if len(password) < 12:
        raise ValueError("Platform administrator password must have at least 12 characters")

    db.info.pop("organization_id", None)
    seed_roles(db)
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR_PLATAFORMA").with_for_update())
    if role is None or role.estado.upper() != "ACTIVO":
        raise ValueError("The protected platform administrator role is unavailable or inactive")
    existing = db.scalar(select(Usuario).where(Usuario.correo == normalized_email))
    if existing is not None:
        if existing.id_organizacion is None and existing.id_rol == role.id_rol:
            return existing, False
        raise ValueError("The requested email already belongs to a different account")

    first_admin = db.scalar(select(Usuario).where(Usuario.id_rol == role.id_rol).limit(1))
    if first_admin is not None:
        raise ValueError("A platform administrator already exists; refusing to create another bootstrap account")

    user = Usuario(
        id_organizacion=None,
        id_sucursal=None,
        id_rol=role.id_rol,
        nombres="Administrador",
        apellidos="Plataforma",
        correo=normalized_email,
        password_hash=hash_password(password),
        estado="ACTIVO",
    )
    db.add(user)
    db.flush()
    return user, True
