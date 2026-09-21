from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.preferencia_cliente import PreferenciaCliente, PreferenciaClienteColor
from app.schemas.user import ProfileResponse, ProfileUpdateRequest
from app.services.user_service import UserService

user_router = APIRouter(prefix="/users", tags=["Usuarios"])

class PreferencesRequest(BaseModel):
    talla_superior: str | None = Field(default=None, max_length=50)
    talla_pantalon: str | None = Field(default=None, max_length=50)
    talla_calzado: str | None = Field(default=None, max_length=50)
    id_colores: list[int] = Field(default_factory=list)
    estilos: list[str] = Field(default_factory=list)

def customer_for(user: Usuario, db: Session) -> Cliente:
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if not customer: raise HTTPException(403, "Solo un cliente puede gestionar preferencias")
    return customer

@user_router.get("/profile/preferences")
def get_preferences(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    customer = customer_for(current_user, db); pref = db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.id_cliente == customer.id_cliente))
    if not pref: return {"talla_superior":None,"talla_pantalon":None,"talla_calzado":None,"id_colores":[],"colores":[],"estilos":[]}
    color_ids = db.scalars(select(PreferenciaClienteColor.id_color).where(PreferenciaClienteColor.id_preferencia == pref.id_preferencia)).all()
    colors = db.scalars(select(Color).where(Color.id_color.in_(color_ids))).all() if color_ids else []
    names_by_id = {color.id_color: color.nombre for color in colors}
    return {"talla_superior":pref.talla_superior,"talla_pantalon":pref.talla_pantalon,"talla_calzado":pref.talla_calzado,"id_colores":color_ids,"colores":[names_by_id[color_id] for color_id in color_ids if color_id in names_by_id],"estilos":[x for x in pref.estilos.split(',') if x]}

@user_router.put("/profile/preferences")
def save_preferences(data: PreferencesRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    customer = customer_for(current_user, db)
    if len(set(data.id_colores)) != len(data.id_colores) or any(db.get(Color, color_id) is None for color_id in data.id_colores): raise HTTPException(422, "Color no válido")
    allowed = {"Casual","Formal","Urbano","Deportivo"}
    if not set(data.estilos).issubset(allowed): raise HTTPException(422, "Estilo no válido")
    pref = db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.id_cliente == customer.id_cliente))
    if not pref: pref = PreferenciaCliente(id_cliente=customer.id_cliente); db.add(pref); db.flush()
    pref.talla_superior,pref.talla_pantalon,pref.talla_calzado,pref.estilos=data.talla_superior,data.talla_pantalon,data.talla_calzado,','.join(data.estilos)
    db.query(PreferenciaClienteColor).filter_by(id_preferencia=pref.id_preferencia).delete()
    db.add_all([PreferenciaClienteColor(id_preferencia=pref.id_preferencia,id_color=color_id) for color_id in data.id_colores]); db.commit()
    return get_preferences(db,current_user)

@user_router.delete("/profile/preferences", status_code=204)
def delete_preferences(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    customer = customer_for(current_user, db); pref = db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.id_cliente == customer.id_cliente))
    if pref: db.delete(pref); db.commit()


@user_router.get(
    "/profile",
    response_model=ProfileResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Usuario o cliente no encontrado"}},
)
def get_profile(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)
) -> ProfileResponse:
    usuario = UserService(db).get_profile(current_user.id_usuario)
    return ProfileResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        telefono=usuario.telefono,
    )


@user_router.put(
    "/profile",
    response_model=ProfileResponse,
    responses={
        401: {"description": "Token inválido"},
        404: {"description": "Usuario o cliente no encontrado"},
        500: {"description": "No se pudo actualizar el perfil"},
    },
)
def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ProfileResponse:
    usuario = UserService(db).update_profile(current_user.id_usuario, request)
    return ProfileResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        telefono=usuario.telefono,
    )
