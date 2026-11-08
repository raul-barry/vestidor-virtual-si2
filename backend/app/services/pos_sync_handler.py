"""Idempotent synchronization for cash-only, in-person POS sales."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.pricing_service import current_price
from app.services.sync_handlers import SyncActor, SyncHandlerError, SyncHandlerRegistry


def create_offline_pos_sale(db: Session, actor: SyncActor, payload: dict[str, Any]) -> dict[str, Any]:
    if actor.role not in {"CAJERO", "ADMINISTRADOR"}:
        raise SyncHandlerError("El rol no puede registrar ventas POS.", "NO_AUTORIZADA")
    try:
        branch_id = int(payload["id_sucursal"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Falta una sucursal válida para la venta.", "DATOS_INVALIDOS") from None
    branch = db.scalar(select(Sucursal).where(
        Sucursal.id_sucursal == branch_id,
        Sucursal.id_organizacion == actor.organization_id,
        Sucursal.estado == "ACTIVA",
    ))
    if branch is None:
        raise SyncHandlerError("La sucursal no pertenece a la organización activa.", "NO_AUTORIZADA")
    cashier = db.get(Usuario, actor.user_id)
    if actor.role == "CAJERO" and (cashier is None or cashier.id_sucursal != branch_id):
        raise SyncHandlerError("La sucursal no está asignada al cajero.", "NO_AUTORIZADA")

    customer_id = payload.get("id_cliente")
    if customer_id is not None:
        customer = db.scalar(select(Cliente).join(Usuario).where(
            Cliente.id_cliente == customer_id,
            Usuario.id_organizacion == actor.organization_id,
            Usuario.estado.in_(("activo", "ACTIVO")),
        ))
        if customer is None:
            raise SyncHandlerError("El cliente no pertenece a la organización activa.", "NO_AUTORIZADA")
    customer_type = "CLIENTE_REGISTRADO" if customer_id is not None else "CONSUMIDOR_FINAL"
    nit_ci = str(payload.get("nit_ci") or "").strip() or None
    business_name = str(payload.get("razon_social") or "").strip() or None
    if bool(nit_ci) != bool(business_name):
        raise SyncHandlerError("NIT/CI y razón social deben registrarse juntos.", "DATOS_INVALIDOS")

    lines = payload.get("lineas")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 100:
        raise SyncHandlerError("La venta debe incluir entre 1 y 100 líneas.", "DATOS_INVALIDOS")
    quantities: dict[int, int] = {}
    for line in lines:
        if not isinstance(line, dict):
            raise SyncHandlerError("Formato de línea inválido.", "DATOS_INVALIDOS")
        try:
            variant_id, quantity = int(line["id_variante"]), int(line["cantidad"])
        except (KeyError, TypeError, ValueError):
            raise SyncHandlerError("Cada línea requiere variante y cantidad.", "DATOS_INVALIDOS") from None
        if variant_id < 1 or not 1 <= quantity <= 1000:
            raise SyncHandlerError("Variante o cantidad inválida.", "DATOS_INVALIDOS")
        quantities[variant_id] = quantities.get(variant_id, 0) + quantity
    if len(quantities) != len(lines):
        raise SyncHandlerError("No se permiten variantes duplicadas en el lote POS.", "DATOS_INVALIDOS")

    rows: list[tuple[Inventario, int, Decimal]] = []
    for variant_id, quantity in sorted(quantities.items()):
        inventory = db.scalar(
            select(Inventario)
            .join(Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal)
            .join(ProductoVariante, ProductoVariante.id_variante == Inventario.id_variante)
            .join(Producto, Producto.id_producto == ProductoVariante.id_producto)
            .where(
                Inventario.id_sucursal == branch_id,
                Inventario.id_variante == variant_id,
                Sucursal.id_organizacion == actor.organization_id,
                Producto.id_organizacion == actor.organization_id,
            )
            .with_for_update(of=Inventario)
        )
        if (inventory is None or inventory.stock_disponible < quantity
                or inventory.variante.estado != "ACTIVO" or inventory.variante.producto.estado != "ACTIVO"):
            raise SyncHandlerError("Stock insuficiente o variante inactiva.", "CONFLICTO_INVENTARIO")
        rows.append((inventory, quantity, current_price(db, inventory.variante.producto)))

    total = sum((price * quantity for _, quantity, price in rows), Decimal("0.00")).quantize(Decimal("0.01"))
    try:
        received = Decimal(str(payload["importe_recibido"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise SyncHandlerError("Para la venta offline se requiere el efectivo recibido.", "DATOS_INVALIDOS") from None
    if not received.is_finite() or received < total or received > Decimal("99999999.99"):
        raise SyncHandlerError("El efectivo recibido es insuficiente o está fuera de rango.", "DATOS_INVALIDOS")

    order = Pedido(
        id_vendedor=actor.user_id, id_cliente=customer_id, estado="ENTREGADO", total=total,
        tipo_cliente=customer_type, tipo_venta="PRESENCIAL", nit_ci=nit_ci, razon_social=business_name,
        tipo_entrega="RECOJO_SUCURSAL", id_sucursal_entrega=branch_id,
    )
    db.add(order)
    db.flush([order])
    for inventory, quantity, price in rows:
        previous = inventory.stock_disponible
        inventory.stock_disponible -= quantity
        inventory.stock_vendido += quantity
        db.add(PedidoDetalle(
            id_pedido=order.id_pedido, id_variante=inventory.id_variante,
            cantidad=quantity, precio_unitario=price,
        ))
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario, tipo_movimiento="SALIDA", cantidad=quantity,
            stock_anterior=previous, stock_nuevo=inventory.stock_disponible,
            motivo=f"Venta presencial offline pedido {order.id_pedido}", id_usuario=actor.user_id,
        ))
    payment = Pago(
        id_pedido=order.id_pedido, metodo_pago="EFECTIVO", monto=total,
        estado="PAGADO", cash_received=received, cash_change=(received - total).quantize(Decimal("0.01")),
    )
    db.add(payment)
    AuditService.record(
        db, organization_id=actor.organization_id, actor_id=actor.user_id, actor_role=actor.role,
        action="VENTA_POS_OFFLINE_REGISTRADA", entity="Pedido", entity_id=order.id_pedido,
        result="PAGADO", details={"metodo_pago": "EFECTIVO", "total": str(total), "id_sucursal": branch_id},
        dedupe_key=f"pos-sale:{actor.organization_id}:{order.id_pedido}",
    )
    return {"id_pedido": order.id_pedido, "estado": order.estado, "total": str(total),
            "metodo_pago": "EFECTIVO", "estado_pago": payment.estado,
            "cash_received": str(received), "cash_change": str(payment.cash_change)}


def register_pos_handlers(registry: SyncHandlerRegistry) -> None:
    registry.register("pos.venta_contado", create_offline_pos_sale)
