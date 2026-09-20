from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.bitacora import Bitacora
from app.models.comercio import Coleccion, Proveedor
from app.models.producto import Producto
from app.models.usuario import Usuario

commercial_master_admin_router = APIRouter(prefix="/admin", tags=["Administración comercial"])


class SupplierRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str = Field(default="", max_length=500)
    persona_contacto: str = Field(default="", max_length=150)
    telefono: str = Field(default="", max_length=30)
    correo: str = Field(default="", max_length=255)
    direccion: str = Field(default="", max_length=255)
    estado: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"


class CollectionRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str = Field(default="", max_length=255)
    temporada: str = Field(default="", max_length=80)
    anio: int | None = Field(default=None, ge=1900, le=2200)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"

    @model_validator(mode="after")
    def validate_dates(self) -> "CollectionRequest":
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha final debe ser posterior a la fecha inicial")
        return self


class StateRequest(BaseModel):
    estado: Literal["ACTIVO", "INACTIVO"]


def serialize(row: Proveedor | Coleccion | Producto) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un registro con ese nombre") from exc


@commercial_master_admin_router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), _: Usuario = Depends(get_current_admin)) -> list[dict]:
    return [serialize(row) for row in db.scalars(select(Proveedor).order_by(Proveedor.nombre)).all()]


@commercial_master_admin_router.post("/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(
    data: SupplierRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    values = data.model_dump()
    row = Proveedor(**values, contacto=values["persona_contacto"])
    db.add(row)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Creación proveedor: {data.nombre}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.put("/suppliers/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: SupplierRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    row = db.get(Proveedor, supplier_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    row.contacto = data.persona_contacto
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Edición proveedor: {supplier_id}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.patch("/suppliers/{supplier_id}/status")
def update_supplier_status(
    supplier_id: int,
    data: StateRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    row = db.get(Proveedor, supplier_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    row.estado = data.estado
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Estado proveedor {supplier_id}: {data.estado}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.get("/collections")
def list_collections(db: Session = Depends(get_db), _: Usuario = Depends(get_current_admin)) -> list[dict]:
    return [serialize(row) for row in db.scalars(select(Coleccion).order_by(Coleccion.nombre)).all()]


@commercial_master_admin_router.post("/collections", status_code=status.HTTP_201_CREATED)
def create_collection(
    data: CollectionRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    row = Coleccion(**data.model_dump())
    db.add(row)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Creación colección: {data.nombre}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.put("/collections/{collection_id}")
def update_collection(
    collection_id: int,
    data: CollectionRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    row = db.get(Coleccion, collection_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Colección no encontrada")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Edición colección: {collection_id}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.patch("/collections/{collection_id}/status")
def update_collection_status(
    collection_id: int,
    data: StateRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    row = db.get(Coleccion, collection_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Colección no encontrada")
    row.estado = data.estado
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Estado colección {collection_id}: {data.estado}"))
    commit(db)
    return serialize(row)


@commercial_master_admin_router.get("/collections/{collection_id}/products")
def collection_products(
    collection_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> list[dict]:
    if not db.get(Coleccion, collection_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Colección no encontrada")
    rows = db.scalars(select(Producto).where(Producto.id_coleccion == collection_id).order_by(Producto.nombre)).all()
    return [serialize(row) for row in rows]


@commercial_master_admin_router.put("/collections/{collection_id}/products/{product_id}")
def associate_collection_product(
    collection_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    collection = db.get(Coleccion, collection_id)
    product = db.get(Producto, product_id)
    if not collection or not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Colección o producto no encontrado")
    product.id_coleccion = collection_id
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Producto {product_id} asociado a colección {collection_id}"))
    db.commit()
    return serialize(product)


@commercial_master_admin_router.delete("/collections/{collection_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collection_product(
    collection_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> None:
    product = db.get(Producto, product_id)
    if not product or product.id_coleccion != collection_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no asociado a esta colección")
    product.id_coleccion = None
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Producto {product_id} quitado de colección {collection_id}"))
    db.commit()
