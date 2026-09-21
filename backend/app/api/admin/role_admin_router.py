from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.rol import Permiso, Rol

role_admin_router = APIRouter(prefix="/admin/roles", tags=["Administración de roles"])
BASE_ROLES = {"ADMINISTRADOR", "CLIENTE", "ENCARGADO_SUCURSAL", "CAJERO"}

class RoleRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    permisos: list[int] = Field(default_factory=list)

def response(role: Rol):
    return {"id_rol":role.id_rol,"nombre":role.nombre,"descripcion":role.descripcion,"estado":role.estado,"protegido":role.nombre in BASE_ROLES,"permisos":[{"id_permiso":p.id_permiso,"codigo":p.codigo,"descripcion":p.descripcion} for p in role.permisos]}

@role_admin_router.get("")
def list_roles(db: Session=Depends(get_db), _=Depends(get_current_admin)):
    return [response(role) for role in db.scalars(select(Rol).order_by(Rol.nombre)).unique().all()]

@role_admin_router.get("/permissions")
def list_permissions(db: Session=Depends(get_db), _=Depends(get_current_admin)):
    return [{"id_permiso":p.id_permiso,"codigo":p.codigo,"descripcion":p.descripcion} for p in db.scalars(select(Permiso).order_by(Permiso.codigo)).all()]

@role_admin_router.post("", status_code=201)
def create_role(data: RoleRequest, db: Session=Depends(get_db), _=Depends(get_current_admin)):
    name=data.nombre.strip().upper()
    if db.scalar(select(Rol).where(Rol.nombre==name)): raise HTTPException(409,"El rol ya existe")
    permissions=list(db.scalars(select(Permiso).where(Permiso.id_permiso.in_(data.permisos))).all()) if data.permisos else []
    if len(permissions)!=len(set(data.permisos)): raise HTTPException(422,"Permiso no válido")
    role=Rol(nombre=name,descripcion=data.descripcion,estado="ACTIVO",permisos=permissions);db.add(role);db.commit();db.refresh(role);return response(role)

@role_admin_router.put("/{role_id}")
def update_role(role_id:int,data:RoleRequest,db:Session=Depends(get_db),_=Depends(get_current_admin)):
    role=db.get(Rol,role_id)
    if not role: raise HTTPException(404,"Rol no encontrado")
    name=data.nombre.strip().upper()
    if role.nombre in BASE_ROLES and name!=role.nombre: raise HTTPException(422,"No se puede renombrar un rol base")
    duplicate=db.scalar(select(Rol).where(Rol.nombre==name,Rol.id_rol!=role_id))
    if duplicate: raise HTTPException(409,"El rol ya existe")
    permissions=list(db.scalars(select(Permiso).where(Permiso.id_permiso.in_(data.permisos))).all()) if data.permisos else []
    if len(permissions)!=len(set(data.permisos)): raise HTTPException(422,"Permiso no válido")
    role.nombre=name;role.descripcion=data.descripcion;role.permisos=permissions;db.commit();db.refresh(role);return response(role)

@role_admin_router.patch("/{role_id}/toggle-status")
def toggle_role(role_id:int,db:Session=Depends(get_db),_=Depends(get_current_admin)):
    role=db.get(Rol,role_id)
    if not role: raise HTTPException(404,"Rol no encontrado")
    if role.nombre in BASE_ROLES: raise HTTPException(422,"Los roles base no se pueden desactivar")
    role.estado="INACTIVO" if role.estado=="ACTIVO" else "ACTIVO";db.commit();db.refresh(role);return response(role)
