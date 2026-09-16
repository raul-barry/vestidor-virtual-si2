from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario


def consume_order_stock(db, order):
    """Called inside the payment transaction; lock inventory in a stable order."""
    required = {}
    for detail in order.detalles:
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
        db.add(MovimientoInventario(id_inventario=inv.id_inventario,
            tipo_movimiento="SALIDA", cantidad=quantity, stock_anterior=previous,
            stock_nuevo=inv.stock_disponible, motivo=f"Pedido {order.id_pedido}",
            id_usuario=order.cliente.id_usuario))
