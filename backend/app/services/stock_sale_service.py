from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.reserva import Reserva
from app.models.pedido_detalle import PedidoDetalle
from app.models.pedido import Pedido


def consume_order_stock(db, order):
    """Called inside the payment transaction; lock inventory in a stable order."""
    required = {}
    reserved_details = []
    for detail in order.detalles:
        if detail.id_reserva is not None:
            reservation = db.scalar(
                select(Reserva).where(Reserva.id_reserva == detail.id_reserva).with_for_update()
            )
            if (reservation is None or reservation.id_usuario != order.cliente.id_usuario
                    or reservation.id_pedido not in (None, order.id_pedido)
                    or reservation.estado not in ("PENDIENTE", "RESERVADA", "CONFIRMADA")
                    or reservation.cantidad != detail.cantidad):
                raise AppException("La reserva asociada no está disponible para vender", status_code=409)
            reserved_details.append((detail, reservation))
        else:
            required[detail.id_variante] = required.get(detail.id_variante, 0) + detail.cantidad

    allocations = []
    for variant_id, quantity in sorted(required.items()):
        inventories = db.scalars(select(Inventario).where(
            Inventario.id_variante == variant_id
        ).order_by(Inventario.id_inventario).with_for_update()).all()
        inventories = [i for i in inventories if i.sucursal.estado == "ACTIVA"]
        if sum(i.stock_disponible for i in inventories) < quantity:
            raise AppException("Stock insuficiente para aprobar el pago", status_code=409)
        for inv in inventories:
            take = min(quantity, inv.stock_disponible)
            if take:
                allocations.append((inv, take))
                quantity -= take
    for inv, quantity in allocations:
        previous = inv.stock_disponible
        inv.stock_disponible -= quantity
        inv.stock_vendido += quantity
        db.add(MovimientoInventario(id_inventario=inv.id_inventario,
            tipo_movimiento="SALIDA", cantidad=quantity, stock_anterior=previous,
            stock_nuevo=inv.stock_disponible, motivo=f"Pedido {order.id_pedido}",
            id_usuario=order.cliente.id_usuario))

    for detail, reservation in reserved_details:
        inventory = db.scalar(
            select(Inventario).where(Inventario.id_inventario == reservation.id_inventario).with_for_update()
        )
        if inventory is None or inventory.id_variante != detail.id_variante:
            raise AppException("El inventario de la reserva no coincide con el pedido", status_code=409)
        if inventory.stock_reservado < detail.cantidad:
            raise AppException("Stock reservado insuficiente para aprobar el pago", status_code=409)
        inventory.stock_reservado -= detail.cantidad
        inventory.stock_vendido += detail.cantidad
        reservation.estado = "COMPLETADA"
        reservation.id_pedido = order.id_pedido
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario,
            tipo_movimiento="SALIDA",
            cantidad=detail.cantidad,
            stock_anterior=inventory.stock_disponible,
            stock_nuevo=inventory.stock_disponible,
            motivo=f"Pedido {order.id_pedido} - Reserva {reservation.id_reserva}",
            id_usuario=order.cliente.id_usuario,
        ))


def hold_order_stock(db, order, *, ttl: timedelta = timedelta(minutes=15)) -> None:
    """Atomically reserve online order lines before asking a payment provider."""
    if order.estado != "PENDIENTE":
        raise AppException("El pedido no está pendiente", status_code=409)
    for detail in db.scalars(
        select(PedidoDetalle).where(PedidoDetalle.id_pedido == order.id_pedido)
        .order_by(PedidoDetalle.id_detalle).with_for_update()
    ).all():
        if detail.id_reserva is not None:
            reservation = db.scalar(select(Reserva).where(
                Reserva.id_reserva == detail.id_reserva
            ).with_for_update())
            if reservation and reservation.estado in ("PENDIENTE", "RESERVADA", "CONFIRMADA"):
                reservation.fecha_expiracion = datetime.now(timezone.utc) + ttl
                continue
            detail.id_reserva = None
        statement = select(Inventario).where(Inventario.id_variante == detail.id_variante)
        if order.id_sucursal_entrega is not None:
            statement = statement.where(Inventario.id_sucursal == order.id_sucursal_entrega)
        inventories = db.scalars(statement.order_by(Inventario.id_inventario).with_for_update()).all()
        inventory = next((row for row in inventories if row.sucursal.estado == "ACTIVA"
                          and row.stock_disponible >= detail.cantidad), None)
        if inventory is None:
            raise AppException("No hay una sucursal con stock suficiente para proteger esta línea", status_code=409)
        before = inventory.stock_disponible
        inventory.stock_disponible -= detail.cantidad
        inventory.stock_reservado += detail.cantidad
        reservation = Reserva(
            id_usuario=order.cliente.id_usuario,
            id_inventario=inventory.id_inventario,
            id_pedido=order.id_pedido,
            cantidad=detail.cantidad,
            estado="CONFIRMADA",
            fecha=datetime.now(timezone.utc),
            fecha_expiracion=datetime.now(timezone.utc) + ttl,
        )
        db.add(reservation)
        db.flush([reservation])
        detail.id_reserva = reservation.id_reserva
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario, tipo_movimiento="RESERVA",
            cantidad=detail.cantidad, stock_anterior=before,
            stock_nuevo=inventory.stock_disponible,
            motivo=f"Protección temporal de pago pedido {order.id_pedido}",
            id_usuario=order.cliente.id_usuario,
        ))


def release_order_stock(db, order, *, reason: str) -> None:
    """Release only still-held units. Completed sale movements are immutable."""
    details = db.scalars(select(PedidoDetalle).where(
        PedidoDetalle.id_pedido == order.id_pedido
    ).order_by(PedidoDetalle.id_detalle).with_for_update()).all()
    for detail in details:
        if detail.id_reserva is None:
            continue
        reservation = db.scalar(select(Reserva).where(
            Reserva.id_reserva == detail.id_reserva
        ).with_for_update())
        if reservation is None or reservation.estado not in ("PENDIENTE", "RESERVADA", "CONFIRMADA"):
            continue
        inventory = db.scalar(select(Inventario).where(
            Inventario.id_inventario == reservation.id_inventario
        ).with_for_update())
        if inventory is None or inventory.stock_reservado < reservation.cantidad:
            raise AppException("No se pudo liberar la reserva de inventario", status_code=409)
        previous = inventory.stock_disponible
        inventory.stock_reservado -= reservation.cantidad
        inventory.stock_disponible += reservation.cantidad
        reservation.estado = "CANCELADA"
        detail.id_reserva = None
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario, tipo_movimiento="LIBERACION_RESERVA",
            cantidad=reservation.cantidad, stock_anterior=previous,
            stock_nuevo=inventory.stock_disponible, motivo=reason,
            id_usuario=order.cliente.id_usuario,
        ))
