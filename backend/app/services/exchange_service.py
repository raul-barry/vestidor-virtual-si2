from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.exchange import ExchangeInventoryIncident, GarmentExchange, OrganizationHoliday
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.pricing_service import current_price


def _now() -> datetime:
    return datetime.now(timezone.utc)


def business_days_open(db: Session, organization_id: int, delivered: date, today: date) -> int:
    if today <= delivered:
        return 0
    holidays = set(db.scalars(select(OrganizationHoliday.holiday_date).where(
        OrganizationHoliday.organization_id == organization_id,
        OrganizationHoliday.holiday_date > delivered,
        OrganizationHoliday.holiday_date <= today,
    )).all())
    count, current = 0, delivered + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return count


def _purchase_context(db: Session, organization_id: int, customer_id: int, detail_id: int):
    detail = db.scalar(select(PedidoDetalle).where(PedidoDetalle.id_detalle == detail_id).with_for_update())
    if detail is None:
        raise HTTPException(404, "Detalle de compra no encontrado")
    order = db.scalar(select(Pedido).where(Pedido.id_pedido == detail.id_pedido).with_for_update())
    customer = db.get(Cliente, customer_id)
    payment = db.scalar(select(Pago).where(Pago.id_pedido == detail.id_pedido, Pago.estado == "PAGADO"))
    if (order is None or customer is None or order.id_cliente != customer_id or not payment
            or order.estado != "ENTREGADO" or order.fecha_entrega is None):
        raise HTTPException(409, "El pedido debe pertenecer al cliente, estar pagado y tener entrega confirmada")
    delivered_at = order.fecha_entrega
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    if business_days_open(db, organization_id, delivered_at.date(), _now().date()) > 7:
        raise HTTPException(422, "El plazo de siete días hábiles para cambios venció")
    used = db.scalar(select(func.coalesce(func.sum(GarmentExchange.quantity), 0)).where(
        GarmentExchange.organization_id == organization_id,
        GarmentExchange.original_detail_id == detail_id,
        GarmentExchange.state != "RECHAZADO",
    )) or 0
    if used >= detail.cantidad:
        raise HTTPException(409, "La cantidad comprada ya tiene una solicitud de cambio activa")
    original_variant = db.get(ProductoVariante, detail.id_variante)
    return detail, order, customer, payment, delivered_at, original_variant


def _branch(db: Session, organization_id: int, branch_id: int) -> Sucursal:
    branch = db.scalar(select(Sucursal).where(
        Sucursal.id_sucursal == branch_id, Sucursal.id_organizacion == organization_id,
        Sucursal.estado == "ACTIVA",
    ))
    if branch is None:
        raise HTTPException(422, "Sucursal no activa o ajena a la organización")
    return branch


def _variant(db: Session, organization_id: int, variant_id: int) -> ProductoVariante:
    variant = db.scalar(select(ProductoVariante).join(Producto).where(
        ProductoVariante.id_variante == variant_id,
        Producto.id_organizacion == organization_id,
        Producto.estado == "ACTIVO", ProductoVariante.estado == "ACTIVO",
    ))
    if variant is None:
        raise HTTPException(422, "Variante no disponible en la organización")
    return variant


def _inventory(db: Session, branch_id: int, variant_id: int, *, create: bool = False) -> Inventario | None:
    row = db.scalar(select(Inventario).where(
        Inventario.id_sucursal == branch_id, Inventario.id_variante == variant_id,
    ).with_for_update())
    if row is None and create:
        row = Inventario(id_sucursal=branch_id, id_variante=variant_id,
                         stock_disponible=0, stock_reservado=0, stock_vendido=0)
        db.add(row)
        db.flush()
    return row


def _record_move(db: Session, inventory: Inventario, quantity: int, direction: str,
                 actor_id: int, reason: str) -> None:
    before = inventory.stock_disponible
    if direction == "ENTRADA":
        inventory.stock_disponible += quantity
    else:
        if inventory.stock_disponible < quantity:
            raise HTTPException(409, "Inventario sustituto insuficiente")
        inventory.stock_disponible -= quantity
    db.add(MovimientoInventario(
        id_inventario=inventory.id_inventario, tipo_movimiento=direction,
        cantidad=quantity, stock_anterior=before, stock_nuevo=inventory.stock_disponible,
        motivo=reason[:255], id_usuario=actor_id,
    ))


def create_customer_request(db: Session, *, organization_id: int, customer_user_id: int,
                            detail_id: int, branch_id: int, replacement_variant_id: int | None,
                            reason: str, operation_uuid: str | None = None) -> GarmentExchange:
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == customer_user_id))
    if customer is None:
        raise HTTPException(403, "El usuario no es cliente de esta organización")
    detail, order, customer, payment, delivered, original = _purchase_context(
        db, organization_id, customer.id_cliente, detail_id)
    _branch(db, organization_id, branch_id)
    replacement = _variant(db, organization_id, replacement_variant_id) if replacement_variant_id else None
    if replacement and replacement.producto.id_categoria != original.producto.id_categoria:
        raise HTTPException(422, "El cambio debe ser de la misma categoría")
    row = GarmentExchange(
        organization_id=organization_id, operation_uuid=operation_uuid or str(uuid4()),
        customer_id=customer.id_cliente, original_order_id=order.id_pedido,
        original_detail_id=detail.id_detalle, original_variant_id=original.id_variante,
        replacement_variant_id=replacement.id_variante if replacement else None,
        branch_id=branch_id, quantity=1, purchase_date=order.fecha_pedido,
        delivery_date=delivered, requested_at=_now(), reason=reason.strip(),
        inspection_state="PENDIENTE", state="SOLICITADO",
        original_paid_amount=detail.precio_unitario,
    )
    db.add(row)
    db.flush()
    AuditService.record(db, organization_id=organization_id, actor_id=customer_user_id,
        actor_role="CLIENTE", action="CAMBIO_SOLICITADO", entity="CambioPrenda",
        entity_id=row.id, details={"pedido_id": order.id_pedido},
        dedupe_key=f"exchange:{organization_id}:{row.operation_uuid}:requested")
    return row


def _set_economic_state(db: Session, row: GarmentExchange) -> None:
    replacement = _variant(db, row.organization_id, row.replacement_variant_id)
    original = _variant(db, row.organization_id, row.original_variant_id)
    if replacement.producto.id_categoria != original.producto.id_categoria:
        raise HTTPException(422, "El cambio debe ser de la misma categoría")
    price = current_price(db, replacement.producto)
    row.replacement_amount = price
    row.economic_difference = (price - row.original_paid_amount).quantize(Decimal("0.01"))
    if row.economic_difference > 0:
        row.financial_state = "PENDIENTE_COBRO"
        row.state = "PENDIENTE_COBRO"
    elif row.economic_difference < 0:
        row.financial_state = "PENDIENTE_DEVOLUCION"
        row.state = "APROBADO"
    else:
        row.financial_state = "SIN_DIFERENCIA"
        row.state = "APROBADO"


def inspect_exchange(db: Session, row: GarmentExchange, *, actor: Usuario, approved: bool,
                     good_condition: bool, tag_present: bool, rejection_reason: str | None,
                     replacement_variant_id: int | None = None,
                     replacement_branch_id: int | None = None) -> GarmentExchange:
    if row.state not in {"SOLICITADO", "PENDIENTE_INSPECCION", "PENDIENTE_DISPONIBILIDAD"}:
        raise HTTPException(409, "El cambio ya fue inspeccionado o se encuentra en otro estado")
    row.employee_id = actor.id_usuario
    row.garment_good_condition, row.original_tag_present = good_condition, tag_present
    if not approved or not good_condition or not tag_present:
        row.inspection_state = "RECHAZADA"
        row.state = "RECHAZADO"
        row.reconciliation_note = (rejection_reason or "La prenda no cumple condición y etiqueta requeridas")[:1000]
    else:
        row.inspection_state = "APROBADA"
        row.physical_original_received = True
        row.state = "PENDIENTE_INSPECCION"
        original_inventory = _inventory(db, row.branch_id, row.original_variant_id, create=True)
        row.original_inventory_id = original_inventory.id_inventario
        _record_move(db, original_inventory, row.quantity, "ENTRADA", actor.id_usuario,
                     f"Recepción por cambio {row.id}")
        if replacement_variant_id is not None:
            row.replacement_variant_id = replacement_variant_id
        if replacement_branch_id is not None:
            _branch(db, row.organization_id, replacement_branch_id)
            row.replacement_branch_id = replacement_branch_id
        elif row.replacement_branch_id is None:
            row.replacement_branch_id = row.branch_id
        if row.replacement_variant_id is None:
            row.state = "PENDIENTE_DISPONIBILIDAD"
        else:
            replacement = _variant(db, row.organization_id, row.replacement_variant_id)
            original = _variant(db, row.organization_id, row.original_variant_id)
            if replacement.producto.id_categoria != original.producto.id_categoria:
                raise HTTPException(422, "El cambio debe ser de la misma categoría")
            inventory = _inventory(db, row.replacement_branch_id, replacement.id_variante)
            if inventory is None or inventory.stock_disponible < row.quantity:
                row.state = "PENDIENTE_DISPONIBILIDAD"
            else:
                row.replacement_inventory_id = inventory.id_inventario
                _set_economic_state(db, row)
    AuditService.record(db, organization_id=row.organization_id, actor_id=actor.id_usuario,
        actor_role=actor.rol.nombre, action="CAMBIO_INSPECCIONADO", entity="CambioPrenda",
        entity_id=row.id, result="EXITOSO" if row.inspection_state == "APROBADA" else "RECHAZADO",
        dedupe_key=f"exchange:{row.organization_id}:{row.operation_uuid}:inspected")
    return row


def deliver_replacement(db: Session, row: GarmentExchange, *, actor: Usuario) -> GarmentExchange:
    if row.state not in {"APROBADO", "PENDIENTE_DEVOLUCION"} or row.replacement_variant_id is None:
        raise HTTPException(409, "El cambio aún no está listo para entregar")
    if row.financial_state == "PENDIENTE_COBRO":
        raise HTTPException(409, "Debe confirmarse el cobro real antes de entregar")
    inventory = db.scalar(select(Inventario).where(
        Inventario.id_inventario == row.replacement_inventory_id,
        Inventario.id_sucursal == row.branch_id,
    ).with_for_update()) if row.replacement_inventory_id else _inventory(db, row.replacement_branch_id or row.branch_id, row.replacement_variant_id)
    if inventory is None or inventory.stock_disponible < row.quantity:
        row.state = "PENDIENTE_DISPONIBILIDAD"
        row.replacement_inventory_id = inventory.id_inventario if inventory else None
        db.flush()
        return row
    _record_move(db, inventory, row.quantity, "SALIDA", actor.id_usuario,
                 f"Entrega por cambio {row.id}")
    row.replacement_inventory_id = inventory.id_inventario
    row.physical_replacement_delivered = True
    if row.financial_state == "PENDIENTE_DEVOLUCION":
        row.state = "PENDIENTE_DEVOLUCION"
    else:
        row.state = "COMPLETADO"
        row.completed_at = _now()
    AuditService.record(db, organization_id=row.organization_id, actor_id=actor.id_usuario,
        actor_role=actor.rol.nombre, action="CAMBIO_PRENDA_ENTREGADO", entity="CambioPrenda",
        entity_id=row.id, dedupe_key=f"exchange:{row.organization_id}:{row.operation_uuid}:delivered")
    return row


def register_offline_physical_exchange(db: Session, *, organization_id: int, employee: Usuario,
                                       payload: dict) -> dict:
    try:
        detail_id = int(payload["id_detalle"])
        branch_id = int(payload["id_sucursal"])
        replacement_id = int(payload["id_variante_sustituta"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, "Faltan los datos de la operación física") from None
    if payload.get("prenda_recibida") is not True or payload.get("prenda_entregada") is not True:
        raise HTTPException(422, "El registro físico debe declarar recepción y entrega")
    if payload.get("buen_estado") is not True or payload.get("etiqueta_original") is not True:
        raise HTTPException(422, "La prenda no fue aprobada en inspección")
    _branch(db, organization_id, branch_id)
    exchange_id = payload.get("exchange_id")
    existing_exchange = db.scalar(select(GarmentExchange).where(
        GarmentExchange.id == exchange_id,
        GarmentExchange.organization_id == organization_id,
    ).with_for_update()) if exchange_id is not None else None
    if exchange_id is not None and existing_exchange is None:
        raise HTTPException(404, "Solicitud de cambio no encontrada")
    if existing_exchange is not None and (existing_exchange.original_detail_id != detail_id
            or existing_exchange.physical_original_received
            or existing_exchange.state not in {"SOLICITADO", "PENDIENTE_INSPECCION", "PENDIENTE_DISPONIBILIDAD"}):
        raise HTTPException(409, "La solicitud ya fue recibida físicamente o no admite cambios")
    detail = db.scalar(select(PedidoDetalle).where(PedidoDetalle.id_detalle == detail_id).with_for_update())
    if detail is None:
        raise HTTPException(404, "Detalle de compra no encontrado")
    order = db.scalar(select(Pedido).where(Pedido.id_pedido == detail.id_pedido).with_for_update())
    payment = db.scalar(select(Pago).where(Pago.id_pedido == detail.id_pedido, Pago.estado == "PAGADO"))
    if order is None or not payment or order.estado != "ENTREGADO" or order.fecha_entrega is None:
        raise HTTPException(409, "Compra sin pago o entrega confirmados")
    original = _variant(db, organization_id, detail.id_variante)
    replacement = _variant(db, organization_id, replacement_id)
    if replacement.producto.id_categoria != original.producto.id_categoria:
        raise HTTPException(422, "El cambio debe ser de la misma categoría")
    delivered = order.fecha_entrega
    if delivered.tzinfo is None:
        delivered = delivered.replace(tzinfo=timezone.utc)
    if business_days_open(db, organization_id, delivered.date(), _now().date()) > 7:
        raise HTTPException(422, "El plazo de cambio venció")
    already_exchanged = db.scalar(select(func.coalesce(func.sum(GarmentExchange.quantity), 0)).where(
        GarmentExchange.organization_id == organization_id,
        GarmentExchange.original_detail_id == detail_id,
        GarmentExchange.state != "RECHAZADO",
        GarmentExchange.id != (existing_exchange.id if existing_exchange is not None else -1),
    )) or 0
    if already_exchanged >= detail.cantidad:
        raise HTTPException(409, "La cantidad comprada ya tiene un cambio activo")
    if existing_exchange is None:
        row = GarmentExchange(
            organization_id=organization_id, operation_uuid=str(payload.get("operation_uuid") or uuid4()),
            customer_id=order.id_cliente, original_order_id=order.id_pedido,
            original_detail_id=detail.id_detalle, original_variant_id=detail.id_variante,
            replacement_variant_id=replacement.id_variante, branch_id=branch_id,
            replacement_branch_id=branch_id,
            employee_id=employee.id_usuario, quantity=1, purchase_date=order.fecha_pedido,
            delivery_date=delivered, requested_at=_now(), reason=str(payload.get("motivo", "Cambio presencial offline"))[:255],
            inspection_state="APROBADA", garment_good_condition=True, original_tag_present=True,
            original_paid_amount=detail.precio_unitario, physical_replacement_delivered=True,
        )
        db.add(row)
        db.flush()
    else:
        row = existing_exchange
        row.operation_uuid = str(payload.get("operation_uuid") or row.operation_uuid)
        row.branch_id = branch_id
        row.replacement_branch_id = branch_id
        row.replacement_variant_id = replacement.id_variante
        row.employee_id = employee.id_usuario
        row.inspection_state = "APROBADA"
        row.garment_good_condition = True
        row.original_tag_present = True
        row.physical_replacement_delivered = True
        row.state = "PENDIENTE_INSPECCION"
    incoming = _inventory(db, branch_id, original.id_variante, create=True)
    row.original_inventory_id = incoming.id_inventario
    _record_move(db, incoming, 1, "ENTRADA", employee.id_usuario, f"Recepción por cambio offline {row.id}")
    row.physical_original_received = True
    outgoing = _inventory(db, branch_id, replacement.id_variante)
    _set_economic_state(db, row)
    if outgoing is not None and outgoing.stock_disponible >= 1:
        row.replacement_inventory_id = outgoing.id_inventario
        _record_move(db, outgoing, 1, "SALIDA", employee.id_usuario, f"Entrega por cambio offline {row.id}")
        if row.economic_difference == 0:
            row.state, row.completed_at = "COMPLETADO", _now()
        elif row.economic_difference < 0:
            row.state = "PENDIENTE_DEVOLUCION"
    else:
        row.state = "INCIDENCIA_CONCILIACION"
        row.reconciliation_note = "La entrega física de la variante sustituta se registró offline, pero el stock confirmado no alcanzaba. No se redujo el inventario por debajo de cero."
        incident = ExchangeInventoryIncident(
            organization_id=organization_id, exchange_id=row.id,
            operation_uuid=row.operation_uuid, branch_id=branch_id,
            employee_id=employee.id_usuario, variant_id=replacement.id_variante,
            inventory_id=outgoing.id_inventario if outgoing else None,
            direction="SALIDA_FISICA", quantity=1, state="INCIDENCIA_CONCILIACION",
            reason=row.reconciliation_note,
        )
        db.add(incident)
    AuditService.record(db, organization_id=organization_id, actor_id=employee.id_usuario,
        actor_role=employee.rol.nombre, action="CAMBIO_OFFLINE_REGISTRADO", entity="CambioPrenda",
        entity_id=row.id, result=row.state, details={"incident": row.state == "INCIDENCIA_CONCILIACION"},
        dedupe_key=f"exchange:{organization_id}:{row.operation_uuid}:offline")
    return exchange_record(db, row)


def resolve_incident(db: Session, incident: ExchangeInventoryIncident, *, actor: Usuario,
                     actual_stock: int, reason: str) -> ExchangeInventoryIncident:
    if incident.state != "INCIDENCIA_CONCILIACION":
        raise HTTPException(409, "La incidencia ya fue conciliada")
    inventory = _inventory(db, incident.branch_id, incident.variant_id, create=True)
    before = inventory.stock_disponible
    inventory.stock_disponible = actual_stock
    inventory.stock_vendido = max(inventory.stock_vendido, 0)
    db.add(MovimientoInventario(
        id_inventario=inventory.id_inventario, tipo_movimiento="AJUSTE",
        cantidad=abs(actual_stock - before), stock_anterior=before, stock_nuevo=actual_stock,
        motivo=f"Conciliación de cambio {incident.exchange_id}: {reason}"[:255], id_usuario=actor.id_usuario,
    ))
    incident.inventory_id = inventory.id_inventario
    incident.state, incident.resolved_by, incident.resolved_at = "CONCILIADA", actor.id_usuario, _now()
    incident.resolution_note = reason.strip()[:1000]
    exchange = db.get(GarmentExchange, incident.exchange_id)
    if exchange is not None:
        exchange.reconciliation_note = incident.resolution_note
        if exchange.financial_state == "SIN_DIFERENCIA":
            exchange.state, exchange.completed_at = "COMPLETADO", _now()
        elif exchange.financial_state == "DEVOLUCION_COMPLETADA":
            exchange.state, exchange.completed_at = "COMPLETADO", _now()
        elif exchange.financial_state == "PENDIENTE_DEVOLUCION":
            exchange.state = "PENDIENTE_DEVOLUCION"
        elif exchange.financial_state == "PENDIENTE_COBRO":
            exchange.state = "PENDIENTE_COBRO"
    AuditService.record(db, organization_id=incident.organization_id, actor_id=actor.id_usuario,
        actor_role=actor.rol.nombre, action="INCIDENCIA_CAMBIO_CONCILIADA",
        entity="CambioInventarioIncidente", entity_id=incident.id,
        dedupe_key=f"exchange-incident:{incident.id}:resolved")
    return incident


def _staff_exchange_branch(db: Session, order: Pedido, detail: PedidoDetalle,
                           staff: Usuario) -> Sucursal | None:
    """Resolve the branch where the sold line was fulfilled, without guessing across tenants."""
    if detail.id_reserva is not None:
        reservation = db.get(Reserva, detail.id_reserva)
        if reservation is not None:
            inventory = db.get(Inventario, reservation.id_inventario)
            if inventory is not None:
                return db.scalar(select(Sucursal).where(
                    Sucursal.id_sucursal == inventory.id_sucursal,
                    Sucursal.id_organizacion == staff.id_organizacion,
                ))
    if order.id_sucursal_entrega is not None:
        branch = db.scalar(select(Sucursal).where(
            Sucursal.id_sucursal == order.id_sucursal_entrega,
            Sucursal.id_organizacion == staff.id_organizacion,
        ))
        if branch is not None:
            return branch
    # POS records its branch on Pedido. Older online records may only retain the
    # inventory movement, so use an exact sale reference if available.
    variants = select(Inventario.id_inventario).where(
        Inventario.id_variante == detail.id_variante,
    )
    movement = db.scalar(select(MovimientoInventario).where(
        MovimientoInventario.id_inventario.in_(variants),
        MovimientoInventario.motivo.in_((
            f"Pedido {order.id_pedido}",
            f"Venta presencial pedido {order.id_pedido}",
            f"Venta presencial offline pedido {order.id_pedido}",
        )),
    ).order_by(MovimientoInventario.id_movimiento).limit(1))
    if movement is not None:
        inventory = db.get(Inventario, movement.id_inventario)
        if inventory is not None:
            return db.scalar(select(Sucursal).where(
                Sucursal.id_sucursal == inventory.id_sucursal,
                Sucursal.id_organizacion == staff.id_organizacion,
            ))
    if staff.rol.nombre in {"ENCARGADO_SUCURSAL", "CAJERO"} and staff.id_sucursal is not None:
        return db.scalar(select(Sucursal).where(
            Sucursal.id_sucursal == staff.id_sucursal,
            Sucursal.id_organizacion == staff.id_organizacion,
            Sucursal.estado == "ACTIVA",
        ))
    return None


def staff_sale_record(db: Session, *, sale_id: int, staff: Usuario) -> dict:
    """Return tenant-scoped sale data and same-category replacement options."""
    order = db.scalar(select(Pedido).where(Pedido.id_pedido == sale_id))
    if order is None:
        raise HTTPException(404, "No se encontró una venta con ese código")
    payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido))
    confirmed_at = (payment.fecha_pago if payment and payment.estado == "PAGADO" else order.fecha_pedido)
    if confirmed_at.tzinfo is None:
        confirmed_at = confirmed_at.replace(tzinfo=timezone.utc)
    age_days = (_now().date() - confirmed_at.date()).days
    state_valid = order.estado in {"CONFIRMADO", "CONFIRMADA", "ENTREGADO"}
    payment_valid = payment is not None and payment.estado == "PAGADO"
    period_valid = 0 <= age_days <= 7
    reason = None
    if not state_valid:
        reason = "La venta todavía no está confirmada."
    elif not payment_valid:
        reason = "La venta no tiene un pago confirmado."
    elif age_days > 7:
        reason = f"El plazo de 7 días venció. La venta se confirmó el {confirmed_at.date().isoformat()}."
    elif age_days < 0:
        reason = "La fecha de confirmación de la venta no es válida."

    details = db.scalars(select(PedidoDetalle).where(
        PedidoDetalle.id_pedido == order.id_pedido,
    ).order_by(PedidoDetalle.id_detalle)).all()
    lines = []
    for detail in details:
        original = db.get(ProductoVariante, detail.id_variante)
        if original is None or original.producto.id_organizacion != staff.id_organizacion:
            continue
        branch = _staff_exchange_branch(db, order, detail, staff)
        if branch is None or (staff.rol.nombre in {"ENCARGADO_SUCURSAL", "CAJERO"}
                              and branch.id_sucursal != staff.id_sucursal):
            continue
        used = db.scalar(select(func.coalesce(func.sum(GarmentExchange.quantity), 0)).where(
            GarmentExchange.original_detail_id == detail.id_detalle,
            GarmentExchange.state != "RECHAZADO",
        )) or 0
        remaining = max(0, detail.cantidad - used)
        variants = db.scalars(select(ProductoVariante).join(Producto).where(
            Producto.id_organizacion == staff.id_organizacion,
            Producto.id_categoria == original.producto.id_categoria,
            Producto.estado == "ACTIVO", ProductoVariante.estado == "ACTIVO",
            ProductoVariante.id_variante != original.id_variante,
        ).order_by(Producto.nombre, ProductoVariante.id_variante)).all()
        options = []
        for variant in variants:
            available = db.scalar(select(Inventario.stock_disponible).where(
                Inventario.id_sucursal == branch.id_sucursal,
                Inventario.id_variante == variant.id_variante,
            )) or 0
            options.append({
                "id_variante": variant.id_variante,
                "producto": variant.producto.nombre,
                "talla": variant.talla.nombre,
                "color": variant.color.nombre,
                "stock_disponible": available,
            })
        lines.append({
            "id_detalle": detail.id_detalle,
            "id_variante": original.id_variante,
            "producto": original.producto.nombre,
            "talla": original.talla.nombre,
            "color": original.color.nombre,
            "cantidad_comprada": detail.cantidad,
            "cantidad_disponible_para_cambio": remaining,
            "sucursal": branch.nombre,
            "id_sucursal": branch.id_sucursal,
            "variantes_sustitutas": options,
        })
    return {
        "id_pedido": order.id_pedido,
        "codigo": f"PED-{order.id_pedido}",
        "fecha_confirmacion": confirmed_at.isoformat(),
        "estado": order.estado,
        "estado_pago": payment.estado if payment else "SIN_PAGO",
        "elegible": state_valid and payment_valid and period_valid,
        "motivo_no_elegible": reason,
        "detalles": lines,
    }


def register_staff_exchange(db: Session, *, staff: Usuario, detail_id: int,
                            replacement_variant_id: int, quantity: int, reason: str,
                            operation_uuid: UUID) -> GarmentExchange:
    """Register a same-value, in-branch exchange with one atomic stock transaction."""
    operation_id = str(operation_uuid)
    previous = db.scalar(select(GarmentExchange).where(
        GarmentExchange.organization_id == staff.id_organizacion,
        GarmentExchange.operation_uuid == operation_id,
    ))
    if previous is not None:
        if (previous.original_detail_id != detail_id
                or previous.replacement_variant_id != replacement_variant_id
                or previous.quantity != quantity or previous.reason != reason.strip()):
            raise HTTPException(409, "El identificador de operación ya se usó con otros datos")
        return previous

    detail = db.scalar(select(PedidoDetalle).where(
        PedidoDetalle.id_detalle == detail_id,
    ).with_for_update())
    if detail is None:
        raise HTTPException(404, "Detalle de venta no encontrado")
    order = db.scalar(select(Pedido).where(
        Pedido.id_pedido == detail.id_pedido,
    ).with_for_update())
    if order is None:
        raise HTTPException(404, "No se encontró una venta con ese código")
    sale = staff_sale_record(db, sale_id=order.id_pedido, staff=staff)
    if not sale["elegible"]:
        raise HTTPException(422, sale["motivo_no_elegible"] or "La venta no admite cambios")
    line = next((item for item in sale["detalles"] if item["id_detalle"] == detail_id), None)
    if line is None:
        raise HTTPException(404, "Detalle de venta no encontrado")
    if quantity < 1 or quantity > line["cantidad_disponible_para_cambio"]:
        raise HTTPException(409, "La cantidad supera las unidades disponibles para cambio")
    branch_id = line["id_sucursal"]
    original = _variant(db, staff.id_organizacion, detail.id_variante)
    replacement = _variant(db, staff.id_organizacion, replacement_variant_id)
    if replacement.id_variante == original.id_variante:
        raise HTTPException(422, "Selecciona una variante distinta a la vendida")
    if replacement.producto.id_categoria != original.producto.id_categoria:
        raise HTTPException(422, "El cambio debe respetar la categoría de la prenda vendida")
    if current_price(db, replacement.producto) != detail.precio_unitario:
        raise HTTPException(409, "La variante tiene una diferencia de precio; tramita el cambio por el flujo de solicitud para conservar la conciliación financiera.")

    inventory_rows = db.scalars(select(Inventario).where(
        Inventario.id_sucursal == branch_id,
        Inventario.id_variante.in_(sorted((original.id_variante, replacement.id_variante))),
    ).order_by(Inventario.id_variante).with_for_update()).all()
    by_variant = {row.id_variante: row for row in inventory_rows}
    original_inventory = by_variant.get(original.id_variante)
    replacement_inventory = by_variant.get(replacement.id_variante)
    if original_inventory is None:
        raise HTTPException(409, "No existe inventario de la prenda vendida en su sucursal")
    if original_inventory.stock_vendido < quantity:
        raise HTTPException(409, "El inventario vendido no coincide con la cantidad de la venta")
    if replacement_inventory is None or replacement_inventory.stock_disponible < quantity:
        raise HTTPException(409, "No hay stock suficiente de la variante solicitada en esta sucursal")

    exchange = GarmentExchange(
        organization_id=staff.id_organizacion,
        operation_uuid=operation_id,
        customer_id=order.id_cliente,
        original_order_id=order.id_pedido,
        original_detail_id=detail.id_detalle,
        original_variant_id=original.id_variante,
        replacement_variant_id=replacement.id_variante,
        branch_id=branch_id,
        replacement_branch_id=branch_id,
        original_inventory_id=original_inventory.id_inventario,
        replacement_inventory_id=replacement_inventory.id_inventario,
        employee_id=staff.id_usuario,
        quantity=quantity,
        purchase_date=order.fecha_pedido,
        delivery_date=order.fecha_entrega or order.fecha_pedido,
        requested_at=_now(), reason=reason.strip(),
        inspection_state="APROBADA", garment_good_condition=True,
        original_tag_present=True, state="COMPLETADO",
        original_paid_amount=detail.precio_unitario,
        replacement_amount=current_price(db, replacement.producto),
        economic_difference=Decimal("0.00"), financial_state="SIN_DIFERENCIA",
        physical_original_received=True, physical_replacement_delivered=True,
        completed_at=_now(),
    )
    db.add(exchange)
    db.flush()
    for inventory, direction in ((original_inventory, "ENTRADA"), (replacement_inventory, "SALIDA")):
        before = inventory.stock_disponible
        if direction == "ENTRADA":
            inventory.stock_disponible += quantity
            inventory.stock_vendido -= quantity
        else:
            inventory.stock_disponible -= quantity
            inventory.stock_vendido += quantity
        db.add(MovimientoInventario(
            id_inventario=inventory.id_inventario, tipo_movimiento=direction,
            cantidad=quantity, stock_anterior=before, stock_nuevo=inventory.stock_disponible,
            motivo=f"Cambio de prenda {exchange.id}: {reason.strip()}"[:255],
            id_usuario=staff.id_usuario,
        ))
    AuditService.record(db, organization_id=staff.id_organizacion,
        actor_id=staff.id_usuario, actor_role=staff.rol.nombre,
        action="CAMBIO_PRENDA_REGISTRADO", entity="CambioPrenda", entity_id=exchange.id,
        result="COMPLETADO", details={"pedido_id": order.id_pedido, "cantidad": quantity},
        dedupe_key=f"exchange:{staff.id_organizacion}:{operation_id}:staff-completed")
    return exchange


def exchange_record(db: Session, row: GarmentExchange) -> dict:
    original = db.get(ProductoVariante, row.original_variant_id)
    replacement = db.get(ProductoVariante, row.replacement_variant_id) if row.replacement_variant_id else None
    branch = db.get(Sucursal, row.branch_id)
    return {
        "id": row.id, "operation_uuid": row.operation_uuid,
        "organization_id": row.organization_id, "customer_id": row.customer_id,
        "original_order_id": row.original_order_id, "original_detail_id": row.original_detail_id,
        "original_variant_id": row.original_variant_id,
        "original_product": original.producto.nombre, "original_size": original.talla.nombre,
        "original_color": original.color.nombre,
        "replacement_variant_id": row.replacement_variant_id,
        "replacement_product": replacement.producto.nombre if replacement else None,
        "replacement_size": replacement.talla.nombre if replacement else None,
        "replacement_color": replacement.color.nombre if replacement else None,
        "branch_id": row.branch_id, "branch_name": branch.nombre,
        "employee_id": row.employee_id,
        "purchase_date": row.purchase_date.isoformat(),
        "delivery_date": row.delivery_date.isoformat(),
        "requested_at": row.requested_at.isoformat(),
        "reason": row.reason, "inspection_state": row.inspection_state,
        "state": row.state, "good_condition": row.garment_good_condition,
        "original_tag_present": row.original_tag_present,
        "original_paid_amount": str(row.original_paid_amount),
        "replacement_amount": str(row.replacement_amount) if row.replacement_amount is not None else None,
        "economic_difference": str(row.economic_difference) if row.economic_difference is not None else None,
        "financial_state": row.financial_state,
        "physical_original_received": row.physical_original_received,
        "physical_replacement_delivered": row.physical_replacement_delivered,
        "reconciliation_note": row.reconciliation_note,
    }
