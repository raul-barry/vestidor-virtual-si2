from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import uuid4
from sqlalchemy import select
from app.models.sesion import Sesion

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload["exp"] = expires_at
    payload["jti"] = str(uuid4())
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    user_id = payload.get("id_usuario") if payload else None
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = UsuarioRepository(db).get_by_id(user_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if usuario.estado.upper() != "ACTIVO":
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    session = db.scalar(select(Sesion).where(Sesion.id_usuario == user_id,
        Sesion.token_jwt == credentials.credentials, Sesion.estado == "ACTIVA"))
    if session is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o revocada")
    expires = session.fecha_expiracion
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sesión expirada")
    return usuario


def require_roles(*allowed_roles: str):
    def role_checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.rol.nombre not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return current_user

    return role_checker


def get_current_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol.nombre != "ADMINISTRADOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    return current_user


def get_current_staff(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol.nombre not in ("ADMINISTRADOR", "ENCARGADO_SUCURSAL"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    return current_user


def require_branch(user: Usuario, branch_id: int) -> None:
    if user.rol.nombre != "ADMINISTRADOR" and (user.id_sucursal is None or user.id_sucursal != branch_id):
        raise HTTPException(status_code=403, detail="Sucursal no asignada al usuario")
