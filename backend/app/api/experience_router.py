from typing import Literal
from app.services.experience_catalog import available_variants, variant_record
from app.services.recommendation_service import RecommendationService
from app.services.virtual_fitting_service import VirtualFittingService
from app.services.fashion_assistant_service import FashionAssistantService

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import get_current_user, get_current_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.models.pedido_detalle import PedidoDetalle
from app.models.pedido import Pedido
from app.models.cliente import Cliente
from app.models.producto_variante import ProductoVariante
from app.models.bitacora import Bitacora
from app.models.sesion import Sesion
from app.models.sucursal import Sucursal
from app.services.pricing_service import current_price

experience_router = APIRouter(prefix="/experience", tags=["Recomendaciones, vestidor y seguridad"])


class BranchAssignment(BaseModel):
    id_sucursal: int | None = Field(default=None, gt=0)

class FashionAssistantRequest(BaseModel):
    mensaje: str = Field(min_length=1,max_length=300)

@experience_router.post("/fashion-assistant")
def fashion_assistant(data:FashionAssistantRequest,db:Session=Depends(get_db),user:Usuario=Depends(get_current_user)):
    return FashionAssistantService(db).ask(user.id_usuario,data.mensaje)


@experience_router.get("/staff")
def staff(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return {"usuarios": [dict(id_usuario=u.id_usuario, nombre=f"{u.nombres} {u.apellidos}",
                             rol=u.rol.nombre, id_sucursal=u.id_sucursal)
                         for u in db.scalars(select(Usuario)).all() if u.rol.nombre in ("CAJERO", "ENCARGADO_SUCURSAL", "ENCARGADO")],
            "sucursales": [dict(id_sucursal=s.id_sucursal, nombre=s.nombre) for s in db.scalars(select(Sucursal)).all()]}


@experience_router.put("/staff/{user_id}")
def assign_branch(user_id: int, data: BranchAssignment, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    employee = db.get(Usuario, user_id)
    if not employee or employee.rol.nombre not in ("CAJERO", "ENCARGADO_SUCURSAL", "ENCARGADO"):
        raise HTTPException(404, "Empleado no encontrado")
    if data.id_sucursal is not None and db.get(Sucursal, data.id_sucursal) is None:
        raise HTTPException(404, "Sucursal no encontrada")
    employee.id_sucursal = data.id_sucursal
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Asignación de sucursal usuario {user_id}: {data.id_sucursal}"))
    db.commit()
    return {"message": "Sucursal asignada"}


@experience_router.get("/recommendations")
def recommendations(talla: str = Query(default="", max_length=50), color: str = Query(default="", max_length=50),
                    categoria: str = Query(default="", max_length=100), db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    return RecommendationService(db).recommend(user.id_usuario, talla, color, categoria)


@experience_router.get("/fitting")
def fitting(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    return VirtualFittingService(db).list_variants()


class FittingRequest(BaseModel):
    id_variante: int = Field(gt=0)


@experience_router.post("/fitting")
def start_fitting(data: FittingRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    variant = next((v for v in available_variants(db) if v.id_variante == data.id_variante), None)
    if not variant or not variant_record(db, variant)['garment']:
        raise HTTPException(404, "Prenda compatible no disponible")
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Vestidor virtual: variante {data.id_variante}"))
    db.commit()
    return variant_record(db, variant)


@experience_router.get("/sessions")
def sessions(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return [dict(id_sesion=s.id_sesion, id_usuario=s.id_usuario, inicio=s.fecha_inicio,
                 expiracion=s.fecha_expiracion, estado=s.estado)
            for s in db.scalars(select(Sesion).order_by(Sesion.id_sesion.desc()).limit(500)).all()]


@experience_router.delete("/sessions/{session_id}")
def revoke(session_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    session = db.get(Sesion, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    session.estado = "INACTIVA"
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Revocación de sesión {session_id}"))
    db.commit()
    return {"message": "Sesión revocada"}


class PreferenceSignal(BaseModel):
    tipo: Literal["vista", "seleccion", "favorita"]
    id_producto: int = Field(gt=0)
    id_variante: int | None = Field(default=None, gt=0)


@experience_router.post("/preferences", status_code=201)
def preference(data: PreferenceSignal, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    RecommendationService(db).record(user.id_usuario, data.tipo, data.id_producto, data.id_variante)
    return {"message": "Preferencia guardada"}


@experience_router.get("/virtual-fitting/{producto_id}")
def virtual_fitting(producto_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    return VirtualFittingService(db).get_product(producto_id)
