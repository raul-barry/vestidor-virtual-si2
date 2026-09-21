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
    id_productos: list[int] = Field(default_factory=list)


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


def serialize(row: Proveedor | Coleccion | Producto, db: Session | None = None) -> dict:
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    if isinstance(row, Proveedor) and db is not None:
        data["productos"] = [
            {"id_producto": product.id_producto, "nombre": product.nombre}
            for product in db.scalars(select(Producto).where(Producto.id_proveedor == row.id_proveedor).order_by(Producto.nombre)).all()
        ]
    return data


def set_supplier_products(db: Session, supplier_id: int, product_ids: list[int]) -> None:
    selected = set(product_ids)
    products = db.scalars(select(Producto).where(Producto.id_producto.in_(selected))).all() if selected else []
    if len(products) != len(selected):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Uno de los productos no existe")
    if any(product.id_proveedor not in (None, supplier_id) for product in products):
        raise HTTPException(status.HTTP_409_CONFLICT, "Uno de los productos ya está asociado a otro proveedor")
    for product in db.scalars(select(Producto).where(Producto.id_proveedor == supplier_id)).all():
        if product.id_producto not in selected:
            product.id_proveedor = None
    for product in products:
        product.id_proveedor = supplier_id


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un registro con ese nombre") from exc


@commercial_master_admin_router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), _: Usuario = Depends(get_current_admin)) -> list[dict]:
    return [serialize(row, db) for row in db.scalars(select(Proveedor).order_by(Proveedor.nombre)).all()]


@commercial_master_admin_router.post("/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(
    data: SupplierRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
) -> dict:
    values = data.model_dump(exclude={"id_productos"})
    row = Proveedor(**values, contacto=values["persona_contacto"])
    db.add(row)
    db.flush()
    set_supplier_products(db, row.id_proveedor, data.id_productos)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Creación proveedor: {data.nombre}"))
    commit(db)
    return serialize(row, db)


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
    for key, value in data.model_dump(exclude={"id_productos"}).items():
        setattr(row, key, value)
    row.contacto = data.persona_contacto
    set_supplier_products(db, supplier_id, data.id_productos)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Edición proveedor: {supplier_id}"))
    commit(db)
    return serialize(row, db)


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
