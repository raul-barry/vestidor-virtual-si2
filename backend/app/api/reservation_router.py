from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles, require_branch
from app.database.database import get_db
from app.models.bitacora import Bitacora
from app.models.inventario import Inventario
from app.models.reserva import Reserva
from app.models.usuario import Usuario

reservation_router = APIRouter(prefix="/reservations", tags=["Reservas"])
allowed = require_roles("CLIENTE", "ADMINISTRADOR", "ENCARGADO_SUCURSAL", "ENCARGADO")


class ReservationCreate(BaseModel):
    id_inventario: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000)


class ReservationUpdate(BaseModel):
    estado: Literal["CONFIRMADA", "CANCELADA", "ATENDIDA"]


def present(db, item):
    inv = db.get(Inventario, item.id_inventario)
    return dict(id_reserva=item.id_reserva, id_usuario=item.id_usuario,
                id_inventario=item.id_inventario, cantidad=item.cantidad, estado=item.estado,
                fecha=item.fecha, producto=inv.variante.producto.nombre,
                talla=inv.variante.talla.nombre, color=inv.variante.color.nombre,
                sucursal=inv.sucursal.nombre)


@reservation_router.get("/availability")
def availability(
    id_variante: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user: Usuario = Depends(allowed),
):
    query = select(Inventario).order_by(Inventario.id_inventario)
    if id_variante is not None:
        query = query.where(Inventario.id_variante == id_variante)
    return [dict(id_inventario=i.id_inventario, producto=i.variante.producto.nombre,
                 id_variante=i.id_variante, talla=i.variante.talla.nombre, color=i.variante.color.nombre,
                 sucursal=i.sucursal.nombre, disponible=i.stock_disponible)
            for i in db.scalars(query).all()
            if i.stock_disponible > 0 and i.variante.estado == "ACTIVO"
            and i.variante.producto.estado == "ACTIVO" and i.sucursal.estado == "ACTIVA"]


@reservation_router.get("")
def list_reservations(db: Session = Depends(get_db), user: Usuario = Depends(allowed)):
    query = select(Reserva).order_by(Reserva.id_reserva.desc())
    if user.rol.nombre == "CLIENTE":
        query = query.where(Reserva.id_usuario == user.id_usuario)
    elif user.rol.nombre != "ADMINISTRADOR":
        query = query.join(Inventario).where(Inventario.id_sucursal == user.id_sucursal)
    return [present(db, row) for row in db.scalars(query).all()]


@reservation_router.post("", status_code=201)
def reserve(data: ReservationCreate, db: Session = Depends(get_db),
            user: Usuario = Depends(require_roles("CLIENTE"))):
    inv = db.scalar(select(Inventario).where(Inventario.id_inventario == data.id_inventario).with_for_update())
    if not inv or inv.stock_disponible < data.cantidad or inv.variante.estado != "ACTIVO" or inv.variante.producto.estado != "ACTIVO" or inv.sucursal.estado != "ACTIVA":
        raise HTTPException(409, "Disponibilidad insuficiente")
    inv.stock_disponible -= data.cantidad
    inv.stock_reservado += data.cantidad
    item = Reserva(id_usuario=user.id_usuario, **data.model_dump())
    db.add(item)
    db.add(Bitacora(id_usuario=user.id_usuario, accion="Creación de reserva"))
    db.commit()
    return present(db, item)


@reservation_router.put("/{reservation_id}")
def update(reservation_id: int, data: ReservationUpdate, db: Session = Depends(get_db), user: Usuario = Depends(allowed)):
    item = db.scalar(select(Reserva).where(Reserva.id_reserva == reservation_id).with_for_update())
    if not item or (user.rol.nombre == "CLIENTE" and item.id_usuario != user.id_usuario):
        raise HTTPException(404, "Reserva no encontrada")
    if user.rol.nombre == "CLIENTE" and data.estado != "CANCELADA":
        raise HTTPException(403, "Solo puede cancelar su reserva")
    if user.rol.nombre != "CLIENTE":
        require_branch(user, db.get(Inventario, item.id_inventario).id_sucursal)
    if item.estado in ("CANCELADA", "ATENDIDA") or data.estado == item.estado:
        raise HTTPException(409, "La reserva ya fue procesada")
    if data.estado == "CANCELADA":
        inv = db.scalar(select(Inventario).where(Inventario.id_inventario == item.id_inventario).with_for_update())
        if inv.stock_reservado < item.cantidad:
            raise HTTPException(409, "La reserva no tiene stock reservado")
        inv.stock_reservado -= item.cantidad
        inv.stock_disponible += item.cantidad
    elif data.estado == "ATENDIDA":
        if item.estado != "CONFIRMADA":
            raise HTTPException(409, "Solo se puede atender una reserva confirmada")
        inv = db.scalar(select(Inventario).where(Inventario.id_inventario == item.id_inventario).with_for_update())
        if inv.stock_reservado < item.cantidad:
            raise HTTPException(409, "La reserva no tiene stock reservado")
        inv.stock_reservado -= item.cantidad
    item.estado = data.estado
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Reserva {reservation_id}: {data.estado}"))
    db.commit()
    return present(db, item)
