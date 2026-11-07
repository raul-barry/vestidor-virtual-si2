"""Offline sale handler; prices, tenant and stock are resolved on the server."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
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
from app.models.reserva import Reserva
from app.models.sucursal import Sucursal
from app.core.config import settings
from app.services.stock_sale_service import consume_order_stock
from app.services.audit_service import AuditService
from app.services.pricing_service import current_price
from app.services.sync_handlers import SyncActor, SyncHandlerError, SyncHandlerRegistry


def create_offline_sale(db: Session, actor: SyncActor, payload: dict[str, Any]) -> dict[str, Any]:
    if actor.role != "CLIENTE":
        raise SyncHandlerError("Solo un cliente puede registrar una venta offline.", "NO_AUTORIZADA")
    try:
        owner_id = int(payload["id_usuario"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Falta el usuario de la venta.", "DATOS_INVALIDOS") from None
    if owner_id != actor.user_id:
        raise SyncHandlerError("La venta no pertenece al usuario autenticado.", "NO_AUTORIZADA")

    client = db.scalar(select(Cliente).where(
        Cliente.id_usuario == actor.user_id,
        Cliente.estado.in_(("activo", "ACTIVO")),
    ))
    if client is None:
        raise SyncHandlerError("El cliente no está habilitado para comprar.", "NO_AUTORIZADA")

    lines = payload.get("lineas")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 100:
        raise SyncHandlerError("La venta debe incluir entre 1 y 100 líneas.", "DATOS_INVALIDOS")
    parsed: list[dict[str, Any]] = []
    line_ids: set[str] = set()
    for line in lines:
        if not isinstance(line, dict):
            raise SyncHandlerError("Formato de línea inválido.", "DATOS_INVALIDOS")
        line_id = str(line.get("client_line_id", ""))
        try:
            variant_id = int(line["id_variante"])
            quantity = int(line["cantidad"])
        except (KeyError, TypeError, ValueError):
            raise SyncHandlerError("Cada línea requiere variante y cantidad.", "DATOS_INVALIDOS") from None
        if not line_id or len(line_id) > 100 or line_id in line_ids or variant_id < 1 or not 1 <= quantity <= 1000:
            raise SyncHandlerError("Una línea tiene identificador o cantidad inválidos.", "DATOS_INVALIDOS")
        line_ids.add(line_id)
        parsed.append({"client_line_id": line_id, "id_variante": variant_id, "cantidad": quantity})

    method = str(payload.get("metodo_pago", "EFECTIVO")).upper()
    if method not in {"EFECTIVO", "TARJETA", "QR"}:
        raise SyncHandlerError("Método de pago no válido.", "DATOS_INVALIDOS")
    delivery = payload.get("entrega") or {}
    if not isinstance(delivery, dict):
        raise SyncHandlerError("Datos de entrega inválidos.", "DATOS_INVALIDOS")
    delivery_type = delivery.get("tipo_entrega")
    if delivery_type not in {None, "RECOJO_SUCURSAL", "DELIVERY"}:
        raise SyncHandlerError("Tipo de entrega no válido.", "DATOS_INVALIDOS")
    delivery_data: dict[str, Any] = {"tipo_entrega": delivery_type} if delivery_type else {}
    if delivery_type == "RECOJO_SUCURSAL":
        try:
            branch_id = int(delivery["id_sucursal_entrega"])
        except (KeyError, TypeError, ValueError):
            raise SyncHandlerError("Selecciona una sucursal de recojo válida.", "DATOS_INVALIDOS") from None
        branch = db.scalar(select(Sucursal).where(
            Sucursal.id_sucursal == branch_id,
            Sucursal.id_organizacion == actor.organization_id,
            Sucursal.estado == "ACTIVA",
        ))
        if branch is None:
            raise SyncHandlerError("La sucursal de recojo no pertenece a la organización activa.", "NO_AUTORIZADA")
        delivery_data["id_sucursal_entrega"] = branch_id
    elif delivery_type == "DELIVERY":
        address = str(delivery.get("direccion_entrega", "")).strip()
        phone = str(delivery.get("telefono_entrega", "")).strip()
        if len(address) < 3 or len(address) > 255 or len(phone) < 6 or len(phone) > 30:
            raise SyncHandlerError("Delivery requiere dirección y teléfono válidos.", "DATOS_INVALIDOS")
        delivery_data.update(
            direccion_entrega=address,
            referencia_entrega=str(delivery.get("referencia_entrega", "")).strip()[:255] or None,
            telefono_entrega=phone,
        )

    variant_ids = sorted({line["id_variante"] for line in parsed})
    variants = db.scalars(
        select(ProductoVariante)
        .join(Producto, Producto.id_producto == ProductoVariante.id_producto)
        .where(ProductoVariante.id_variante.in_(variant_ids), Producto.id_organizacion == actor.organization_id)
    ).all()
    variant_by_id = {variant.id_variante: variant for variant in variants}
    # Lock all eligible stock rows in one stable global order before allocating any line.
    inventory_statement = (
        select(Inventario)
        .join(Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal)
        .join(ProductoVariante, ProductoVariante.id_variante == Inventario.id_variante)
        .join(Producto, Producto.id_producto == ProductoVariante.id_producto)
        .where(
            Inventario.id_variante.in_(variant_ids),
            Sucursal.id_organizacion == actor.organization_id,
            Sucursal.estado == "ACTIVA",
            Producto.id_organizacion == actor.organization_id,
        )
        .order_by(Inventario.id_inventario)
        .with_for_update(of=Inventario)
    )
    if delivery_type == "RECOJO_SUCURSAL":
        inventory_statement = inventory_statement.where(
            Inventario.id_sucursal == delivery_data["id_sucursal_entrega"]
        )
    inventory_rows = db.scalars(inventory_statement).all()
    inventory_by_variant: dict[int, list[Inventario]] = {}
    available_by_inventory: dict[int, int] = {}
    for inventory in inventory_rows:
        inventory_by_variant.setdefault(inventory.id_variante, []).append(inventory)
        available_by_inventory[inventory.id_inventario] = max(inventory.stock_disponible, 0)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    allocations: list[tuple[dict[str, Any], Inventario, int, Decimal]] = []
    for line in sorted(parsed, key=lambda item: (item["id_variante"], item["client_line_id"])):
        variant = variant_by_id.get(line["id_variante"])
        if variant is None:
            rejected.append({**line, "motivo": "PRODUCTO_NO_DISPONIBLE"})
            continue
        if variant.estado != "ACTIVO" or variant.producto.estado != "ACTIVO":
            rejected.append({**line, "motivo": "PRODUCTO_NO_DISPONIBLE"})
            continue
        price = current_price(db, variant.producto)
        stock = inventory_by_variant.get(variant.id_variante, [])
        if sum(available_by_inventory[row.id_inventario] for row in stock) < line["cantidad"]:
            rejected.append({**line, "motivo": "CONFLICTO_INVENTARIO"})
            continue
        remaining = line["cantidad"]
        line_allocations = []
        for inventory in stock:
            available = available_by_inventory[inventory.id_inventario]
            amount = min(available, remaining)
            if amount:
                line_allocations.append((inventory, amount))
                available_by_inventory[inventory.id_inventario] -= amount
                remaining -= amount
            if remaining == 0:
                break
        accepted.append({**line, "precio_unitario": str(price), "cantidad_aceptada": line["cantidad"]})
        allocations.extend((line, inventory, amount, price) for inventory, amount in line_allocations)

    if not accepted:
        raise SyncHandlerError(
            "Ningún producto tenía disponibilidad para completar la venta.",
            "CONFLICTO_INVENTARIO",
            result={"pedido": None, "lineas_aceptadas": [], "lineas_rechazadas": rejected, "parcial": False},
        )

    total = sum((price * amount for _, _, amount, price in allocations), Decimal("0.00")).quantize(Decimal("0.01"))
    order = Pedido(
        id_cliente=client.id_cliente,
        estado="PENDIENTE",
        total=total,
        tipo_cliente="CLIENTE_REGISTRADO",
        tipo_venta="ONLINE",
        **delivery_data,
    )
    db.add(order)
    db.flush([order])

    reservations_by_line: dict[str, list[dict[str, Any]]] = {}
    for line, inventory, quantity, price in allocations:
        previous = inventory.stock_disponible
        inventory.stock_disponible -= quantity
        inventory.stock_reservado += quantity
        reservation = Reserva(
            id_usuario=actor.user_id,
            id_inventario=inventory.id_inventario,
            id_pedido=order.id_pedido,
            cantidad=quantity,
            estado="CONFIRMADA",
            fecha=datetime.now(timezone.utc),
            fecha_expiracion=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(reservation)
        db.flush([reservation])
        db.add(PedidoDetalle(
            id_pedido=order.id_pedido,
            id_variante=line["id_variante"],
            id_reserva=reservation.id_reserva,
            cantidad=quantity,
            precio_unitario=price,
        ))
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario,
            tipo_movimiento="RESERVA",
            cantidad=quantity,
            stock_anterior=previous,
            stock_nuevo=inventory.stock_disponible,
            motivo=f"Venta offline {order.id_pedido}",
            id_usuario=actor.user_id,
        ))
        reservations_by_line.setdefault(line["client_line_id"], []).append({
            "cantidad": quantity,
            "id_inventario": inventory.id_inventario,
        })

    payment_data = payload.get("datos_pago") or {}
    if not isinstance(payment_data, dict):
        raise SyncHandlerError("Datos de pago inválidos.", "DATOS_INVALIDOS")
    received = None
    if method == "EFECTIVO" and payment_data.get("importe_recibido") is not None:
        try:
            received = Decimal(str(payment_data["importe_recibido"]))
        except Exception:
            raise SyncHandlerError("Importe recibido inválido.", "DATOS_INVALIDOS") from None
        if not received.is_finite() or received < 0 or received > Decimal("99999999.99"):
            raise SyncHandlerError("Importe recibido fuera de rango.", "DATOS_INVALIDOS")
    payment = Pago(
        id_pedido=order.id_pedido,
        metodo_pago=method,
        monto=total,
        estado="PENDIENTE",
        currency=settings.stripe_currency.upper(),
        cash_received=received,
        cash_change=Decimal("0.00"),
    )
    db.add(payment)
    if method == "EFECTIVO" and received is not None and received >= total:
        # Cash is reconciled against the server-calculated accepted lines only.
        # The cash difference is recorded for the cashier; no rejected line is charged.
        payment.cash_change = (received - total).quantize(Decimal("0.01"))
        payment.estado = "PAGADO"
        payment.fecha_pago = datetime.now(timezone.utc)
        consume_order_stock(db, order)
        order.estado = "CONFIRMADO"
    for line in accepted:
        line["reservas"] = reservations_by_line.get(line["client_line_id"], [])
    AuditService.record(
        db,
        organization_id=actor.organization_id,
        actor_id=actor.user_id,
        actor_role=actor.role,
        action="VENTA_OFFLINE_REGISTRADA",
        entity="Pedido",
        entity_id=order.id_pedido,
        result="PAGADO" if payment.estado == "PAGADO" else "PENDIENTE_PAGO",
        details={"metodo_pago": method, "lineas_aceptadas": len(accepted), "lineas_rechazadas": len(rejected),
                 "estado_pago": payment.estado, "importe_confirmado": str(payment.monto)},
        dedupe_key=f"sale:{actor.organization_id}:{order.id_pedido}",
    )
    return {
        "pedido": {
            "id_pedido": order.id_pedido,
            "estado": order.estado,
            "total": str(total),
            "metodo_pago": method,
            "estado_pago": payment.estado,
            "currency": payment.currency,
            "simulated": payment.simulated,
            "cash_received": str(payment.cash_received) if payment.cash_received is not None else None,
            "cash_change": str(payment.cash_change),
        },
        "lineas_aceptadas": accepted,
        "lineas_rechazadas": rejected,
        "parcial": bool(rejected),
    }


def register_sale_handlers(registry: SyncHandlerRegistry) -> None:
    registry.register("venta.crear", create_offline_sale)
