from typing import Literal
from app.services.experience_catalog import available_variants, variant_record
from app.services.recommendation_service import RecommendationService
from app.services.virtual_fitting_service import VirtualFittingService
from app.services.fashion_assistant_service import FashionAssistantService

import base64
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
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
from app.models.producto import Producto
from app.models.recurso_virtual import RecursoVirtual
from app.schemas.virtual_try_on import VirtualTryOnResponse
from app.services.virtual_try_on_service import GeminiTryOnError, VirtualTryOnService

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


_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
_PHOTO_LIMIT = 8 * 1024 * 1024
_PIL_MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_MAX_PHOTO_PIXELS = 24_000_000
_TRY_ON_RASTER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _try_on_resource_path(resource: RecursoVirtual | None, root: Path) -> Path | None:
    """Return a safe raster asset path, never treating catalogue SVGs as try-on input."""
    if resource is None:
        return None
    path = (root / resource.url_archivo.removeprefix("/api/assets/")).resolve()
    if path.suffix.lower() not in _TRY_ON_RASTER_SUFFIXES:
        return None
    if root not in path.parents or not path.is_file():
        return None
    return path


@experience_router.post("/virtual-try-on", response_model=VirtualTryOnResponse)
async def virtual_try_on_photo(
    product_id: int = Form(..., gt=0),
    variant_id: int | None = Form(default=None, gt=0),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VirtualTryOnResponse:
    """Render an ephemeral photo try-on using Gemini when configured."""
    if photo.content_type not in _PHOTO_TYPES:
        raise HTTPException(422, "Formato no permitido. Usa JPG, PNG o WebP")
    try:
        payload = await photo.read(_PHOTO_LIMIT + 1)
    finally:
        # Starlette may spool uploads to disk; close it before any catalogue or
        # rendering work so a customer photograph is never retained as a file.
        await photo.close()
    if not payload:
        raise HTTPException(422, "Foto vacia")
    if len(payload) > _PHOTO_LIMIT:
        raise HTTPException(413, "La fotografía supera 8 MB" if payload else "Fotografía vacía")
    try:
        with Image.open(BytesIO(payload)) as image:
            actual_mime = _PIL_MIME_TYPES.get(image.format or "")
            if actual_mime != photo.content_type or image.width * image.height > _MAX_PHOTO_PIXELS:
                raise HTTPException(422, "La fotografía debe ser un JPG, PNG o WebP válido de tamaño razonable")
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(422, "El contenido no corresponde a una imagen válida")

    product = db.get(Producto, product_id)
    if product is None or product.estado != "ACTIVO":
        raise HTTPException(404, "Producto no encontrado")
    variant = db.get(ProductoVariante, variant_id) if variant_id else None
    if variant_id and (variant is None or variant.id_producto != product_id or variant.estado != "ACTIVO"):
        raise HTTPException(404, "Variante no encontrada para este producto")
    resource = db.scalar(select(RecursoVirtual).where(
        RecursoVirtual.id_producto == product_id,
        RecursoVirtual.tipo_recurso == "tryon",
        RecursoVirtual.estado == "ACTIVO",
    ).order_by(RecursoVirtual.id.desc()))
    root = Path(__file__).resolve().parents[1] / "assets"
    garment_path = _try_on_resource_path(resource, root)
    if garment_path is None:
        # A normal catalogue JPG/PNG is a compatible fallback when no
        # dedicated cutout is available; SVG catalogue art never is.
        catalogue_resources = db.scalars(select(RecursoVirtual).where(
            RecursoVirtual.id_producto == product_id,
            RecursoVirtual.tipo_recurso == "imagen",
            RecursoVirtual.estado == "ACTIVO",
        ).order_by(RecursoVirtual.id.desc())).all()
        garment_path = next((
            candidate for item in catalogue_resources
            if (candidate := _try_on_resource_path(item, root)) is not None
        ), None)
    if garment_path is None:
        raise HTTPException(422, "No existe una imagen compatible con el vestidor virtual.")
    try:
        result = VirtualTryOnService().render(payload, garment_path, photo.content_type)
    except GeminiTryOnError as exc:
        raise HTTPException(502, str(exc)) from exc
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, "No existe una imagen compatible con el vestidor virtual.")
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Vestidor fotográfico: producto {product_id}"))
    db.commit()
    return VirtualTryOnResponse(
        image_base64=base64.b64encode(result).decode("ascii"), id_producto=product_id,
        id_variante=variant.id_variante if variant else None, nombre=product.nombre,
        talla=variant.talla.nombre if variant else None, color=variant.color.nombre if variant else None,
    )


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
