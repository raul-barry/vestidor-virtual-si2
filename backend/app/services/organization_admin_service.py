import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.organizacion import Organizacion
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.schemas.organization_admin import OrganizationCreate, OrganizationUpdate
from app.services.audit_service import AuditService


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "empresa"


def organization_data(row: Organizacion) -> dict:
    return {
        "id_organizacion": row.id_organizacion,
        "nombre": row.nombre,
        "razon_social": row.razon_social,
        "nit": row.nit,
        "correo_contacto": row.correo_contacto,
        "telefono_contacto": row.telefono_contacto,
        "direccion": row.direccion,
        "logo_url": row.logo_url,
        "slug": row.slug,
        "estado": row.estado,
        "fecha_creacion": row.fecha_creacion.isoformat() if row.fecha_creacion else None,
        "fecha_actualizacion": row.fecha_actualizacion.isoformat() if row.fecha_actualizacion else None,
    }


class OrganizationAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_organizations(self) -> list[dict]:
        rows = self.db.scalars(select(Organizacion).order_by(Organizacion.nombre)).all()
        return [organization_data(row) for row in rows]

    def get_organization(self, organization_id: int) -> Organizacion:
        row = self.db.get(Organizacion, organization_id)
        if row is None:
            raise AppException("Empresa no encontrada", status_code=404)
        return row

    def list_organization_detail(self, organization_id: int) -> dict:
        return organization_data(self.get_organization(organization_id))

    def create_organization(self, data: OrganizationCreate, *, commit: bool = True) -> dict:
        values = data.model_dump()
        name = values.pop("nombre").strip()
        slug = values.pop("slug") or _slugify(name)
        row = Organizacion(nombre=name, slug=slug, estado="ACTIVA", **values)
        self.db.add(row)
        return self._commit_and_present(row, commit=commit)

    def create_first_administrator(self, organization_id: int, data, *, commit: bool = True) -> dict:
        from sqlalchemy import func, select
        from sqlalchemy.exc import IntegrityError
        from app.core.security import hash_password
        from app.models.rol import Rol
        organization = self.get_organization(organization_id)
        if organization.estado != "ACTIVA":
            raise AppException("Empresa no encontrada o inactiva", status_code=404)
        if self.db.scalar(select(Usuario.id_usuario).where(func.lower(Usuario.correo) == data.correo.lower())):
            raise AppException("El correo ya está registrado", status_code=409)
        role = self.db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR", Rol.estado == "ACTIVO"))
        if role is None:
            raise AppException("Rol ADMINISTRADOR no configurado", status_code=500)
        user = Usuario(id_organizacion=organization_id, id_rol=role.id_rol,
                       nombres=data.nombres, apellidos=data.apellidos, correo=data.correo,
                       telefono=data.telefono, password_hash=hash_password(data.password), estado="ACTIVO")
        self.db.add(user)
        try:
            self.db.flush()
            if commit:
                self.db.commit()
        except IntegrityError as exc:
            if commit:
                self.db.rollback()
            raise AppException("No se pudo crear el administrador de empresa", status_code=409) from exc
        if commit:
            self.db.refresh(user)
        return {"id_usuario": user.id_usuario, "id_organizacion": organization_id,
                "nombres": user.nombres, "apellidos": user.apellidos,
                "correo": user.correo, "rol": role.nombre}

    def update_organization(self, organization_id: int, data: OrganizationUpdate) -> dict:
        row = self.get_organization(organization_id)
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(row, key, value)
        row.fecha_actualizacion = datetime.now(timezone.utc)
        return self._commit_and_present(row)

    def set_status(self, organization_id: int, estado: str) -> dict:
        row = self.db.scalar(
            select(Organizacion).where(Organizacion.id_organizacion == organization_id).with_for_update()
        )
        if row is None:
            raise AppException("Empresa no encontrada", status_code=404)
        target = estado.upper()
        current = row.estado.upper()
        if current == target:
            return organization_data(row)
        row.estado = target
        row.fecha_actualizacion = datetime.now(timezone.utc)
        AuditService.record(
            self.db, organization_id=organization_id,
            actor_id=self.db.info.get("audit_actor_id"),
            actor_role=self.db.info.get("audit_actor_role", "ADMINISTRADOR_PLATAFORMA"),
            action="ORGANIZACION_SUSPENDIDA" if target == "INACTIVA" else "ORGANIZACION_REACTIVADA",
            entity="Organizacion", entity_id=organization_id,
            details={"estado_anterior": current, "estado_nuevo": target},
        )
        return self._commit_and_present(row)

    def list_branches(self, organization_id: int) -> list[dict]:
        self.get_organization(organization_id)
        rows = self.db.scalars(
            select(Sucursal).where(Sucursal.id_organizacion == organization_id).order_by(Sucursal.nombre)
        ).all()
        return [{"id_sucursal": row.id_sucursal, "nombre": row.nombre, "direccion": row.direccion,
                 "ciudad": row.ciudad, "estado": row.estado} for row in rows]

    def list_users(self, organization_id: int) -> list[dict]:
        self.get_organization(organization_id)
        inconsistent_assignment = self.db.scalar(
            select(Usuario.id_usuario)
            .outerjoin(Sucursal, Usuario.id_sucursal == Sucursal.id_sucursal)
            .where(
                Usuario.id_organizacion == organization_id,
                Usuario.id_sucursal.is_not(None),
                or_(Sucursal.id_sucursal.is_(None), Sucursal.id_organizacion != organization_id),
            )
            .limit(1)
        )
        if inconsistent_assignment is not None:
            raise AppException("Hay usuarios asignados a sucursales de otra organización", status_code=409)
        rows = self.db.scalars(
            select(Usuario).options(joinedload(Usuario.rol))
            .where(Usuario.id_organizacion == organization_id)
            .order_by(Usuario.apellidos, Usuario.nombres, Usuario.id_usuario)
        ).all()
        return [{"id_usuario": row.id_usuario, "nombre": f"{row.nombres} {row.apellidos}".strip(),
                 "correo": row.correo, "rol": row.rol.nombre, "estado": row.estado,
                 "fecha_registro": row.fecha_registro.isoformat() if row.fecha_registro else None}
                for row in rows]

    def _commit_and_present(self, row: Organizacion, *, commit: bool = True) -> dict:
        try:
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        except IntegrityError as exc:
            if commit:
                self.db.rollback()
            raise AppException("El nombre, slug o NIT de empresa ya está registrado", status_code=409) from exc
        if commit:
            self.db.refresh(row)
        return organization_data(row)
