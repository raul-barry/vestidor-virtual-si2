from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bitacora import Bitacora
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.reserva import Reserva
from app.models.sucursal import Sucursal
from app.services.sync_handlers import SyncActor, SyncHandlerError, SyncHandlerRegistry


def _client(actor: SyncActor, payload: dict[str, Any]) -> None:
    if actor.role != "CLIENTE":
        raise SyncHandlerError("Solo un cliente puede sincronizar reservas.", "NO_AUTORIZADA")
    try:
        owner_id = int(payload["id_usuario"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Falta el usuario original de la reserva.", "DATOS_INVALIDOS") from None
    if owner_id != actor.user_id:
        raise SyncHandlerError("La reserva pertenece a otra sesión de cliente.", "NO_AUTORIZADA")


def create_reservation(db: Session, actor: SyncActor, payload: dict[str, Any]) -> dict[str, Any]:
    _client(actor, payload)
    try:
        inventory_id = int(payload["id_inventario"])
        quantity = int(payload["cantidad"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Se requiere inventario y cantidad válidos.", "DATOS_INVALIDOS") from None
    if inventory_id < 1 or quantity < 1 or quantity > 1000:
        raise SyncHandlerError("Inventario o cantidad fuera de rango.", "DATOS_INVALIDOS")

    inventory = db.scalar(
        select(Inventario)
        .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
        .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
        .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
        .where(
            Inventario.id_inventario == inventory_id,
            Sucursal.id_organizacion == actor.organization_id,
            Producto.id_organizacion == actor.organization_id,
        )
        .with_for_update(of=Inventario)
    )
    if inventory is None:
        raise SyncHandlerError("El inventario no pertenece a la organización autenticada.", "NO_AUTORIZADA")
    if (inventory.variante.estado != "ACTIVO" or inventory.variante.producto.estado != "ACTIVO"
            or inventory.sucursal.estado != "ACTIVA"):
        raise SyncHandlerError("El producto, variante o sucursal no está activo.", "CONFLICTO_ESTADO")
    if inventory.stock_disponible < quantity:
        raise SyncHandlerError("Disponibilidad insuficiente para confirmar la reserva.", "CONFLICTO_INVENTARIO")

    confirmed_at = datetime.now(timezone.utc)
    inventory.stock_disponible -= quantity
    inventory.stock_reservado += quantity
    reservation = Reserva(
        id_usuario=actor.user_id,
        id_inventario=inventory.id_inventario,
        cantidad=quantity,
        estado="PENDIENTE",
        fecha=confirmed_at,
        fecha_expiracion=confirmed_at + timedelta(days=7),
    )
    db.add(reservation)
    db.flush([reservation])
    db.add(Bitacora(id_usuario=actor.user_id, accion=f"Creación offline de reserva {reservation.id_reserva}"))
    return {
        "id_reserva": reservation.id_reserva,
        "estado": reservation.estado,
        "cantidad": reservation.cantidad,
        "id_inventario": inventory.id_inventario,
        "fecha_confirmacion_servidor": confirmed_at.isoformat(),
        "fecha_expiracion_servidor": (confirmed_at + timedelta(days=7)).isoformat(),
    }


def cancel_reservation(db: Session, actor: SyncActor, payload: dict[str, Any]) -> dict[str, Any]:
    _client(actor, payload)
    try:
        reservation_id = int(payload["id_reserva"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Se requiere un ID de reserva válido.", "DATOS_INVALIDOS") from None
    if reservation_id < 1:
        raise SyncHandlerError("El ID de reserva debe ser positivo.", "DATOS_INVALIDOS")

    reservation = db.scalar(
        select(Reserva)
        .join(Inventario, Reserva.id_inventario == Inventario.id_inventario)
        .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
        .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
        .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
        .where(
            Reserva.id_reserva == reservation_id,
            Reserva.id_usuario == actor.user_id,
            Sucursal.id_organizacion == actor.organization_id,
            Producto.id_organizacion == actor.organization_id,
        )
        .with_for_update(of=Reserva)
    )
    if reservation is None:
        raise SyncHandlerError("La reserva no pertenece al usuario y organización autenticados.", "NO_AUTORIZADA")
    if reservation.estado == "CANCELADA":
        return {
            "id_reserva": reservation.id_reserva,
            "estado": "CANCELADA",
            "cantidad": reservation.cantidad,
            "id_inventario": reservation.id_inventario,
            "already_processed": True,
        }
    if reservation.estado in ("COMPLETADA", "ATENDIDA"):
        raise SyncHandlerError("La reserva ya fue cancelada o completada.", "CONFLICTO_ESTADO")
    if reservation.estado not in ("PENDIENTE", "RESERVADA", "CONFIRMADA"):
        raise SyncHandlerError("El estado actual de la reserva no permite cancelarla.", "CONFLICTO_ESTADO")

    inventory = db.scalar(
        select(Inventario)
        .where(Inventario.id_inventario == reservation.id_inventario)
        .with_for_update()
    )
    if inventory is None or inventory.stock_reservado < reservation.cantidad:
        raise SyncHandlerError("El inventario reservado no coincide con la reserva.", "CONFLICTO_INVENTARIO")
    confirmed_at = datetime.now(timezone.utc)
    previous_stock = inventory.stock_disponible
    inventory.stock_reservado -= reservation.cantidad
    inventory.stock_disponible += reservation.cantidad
    reservation.estado = "CANCELADA"
    db.add(MovimientoInventario(
        id_inventario=inventory.id_inventario, tipo_movimiento="LIBERACION_RESERVA",
        cantidad=reservation.cantidad, stock_anterior=previous_stock,
        stock_nuevo=inventory.stock_disponible,
        motivo=f"Cancelación offline de reserva {reservation.id_reserva}",
        id_usuario=actor.user_id,
    ))
    db.add(Bitacora(id_usuario=actor.user_id, accion=f"Cancelación offline de reserva {reservation_id}"))
    return {
        "id_reserva": reservation.id_reserva,
        "estado": reservation.estado,
        "cantidad": reservation.cantidad,
        "id_inventario": reservation.id_inventario,
        "fecha_confirmacion_servidor": confirmed_at.isoformat(),
    }


def register_reservation_handlers(registry: SyncHandlerRegistry) -> None:
    registry.register("reserva.crear", create_reservation)
    registry.register("reserva.cancelar", cancel_reservation)
