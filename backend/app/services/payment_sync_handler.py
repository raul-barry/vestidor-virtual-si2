"""Offline payment requests stop at a pending, server-priced record.

Provider authorization is deliberately performed later through the existing
payment endpoints so no external network request runs inside the sync transaction.
"""
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.services.audit_service import AuditService
from app.services.stock_sale_service import consume_order_stock
from app.services.sync_handlers import SyncActor, SyncHandlerError, SyncHandlerRegistry


def request_offline_payment(db: Session, actor: SyncActor, payload: dict[str, Any]) -> dict[str, Any]:
    if actor.role != "CLIENTE":
        raise SyncHandlerError("Solo el cliente propietario puede solicitar un pago.", "NO_AUTORIZADA")
    if payload.get("id_usuario") != actor.user_id:
        raise SyncHandlerError("El pago no pertenece al usuario autenticado.", "NO_AUTORIZADA")
    try:
        order_id = int(payload["id_pedido"])
    except (KeyError, TypeError, ValueError):
        raise SyncHandlerError("Falta un pedido válido para el pago.", "DATOS_INVALIDOS") from None
    method = str(payload.get("metodo_pago", "")).upper()
    if method not in {"EFECTIVO", "TARJETA", "QR"}:
        raise SyncHandlerError("Método de pago no válido.", "DATOS_INVALIDOS")
    order = db.scalar(select(Pedido).where(Pedido.id_pedido == order_id).with_for_update())
    client = db.scalar(select(Cliente).where(Cliente.id_usuario == actor.user_id))
    if order is None or client is None or order.id_cliente != client.id_cliente:
        raise SyncHandlerError("El pedido no pertenece al cliente.", "NO_AUTORIZADA")
    if order.estado != "PENDIENTE":
        raise SyncHandlerError("El pedido ya no está pendiente de pago.", "CONFLICTO_ESTADO")
    payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido).with_for_update())
    operation_uuid = str(payload.get("_operation_uuid", ""))
    if not operation_uuid:
        raise SyncHandlerError("Falta UUID de idempotencia.", "DATOS_INVALIDOS")
    if payment is not None:
        if payment.idempotency_key == operation_uuid:
            return _result(payment, requires_online=method in {"TARJETA", "QR"})
        raise SyncHandlerError("El pedido ya tiene una solicitud de pago diferente.", "CONFLICTO_ESTADO")

    amount = Decimal(order.total).quantize(Decimal("0.01"))
    received = None
    details = payload.get("datos_pago") or {}
    if not isinstance(details, dict):
        raise SyncHandlerError("Datos de pago inválidos.", "DATOS_INVALIDOS")
    if method == "EFECTIVO" and details.get("importe_recibido") is not None:
        try:
            received = Decimal(str(details["importe_recibido"]))
        except Exception:
            raise SyncHandlerError("Importe de efectivo inválido.", "DATOS_INVALIDOS") from None
        if not received.is_finite() or received < amount or received > Decimal("99999999.99"):
            raise SyncHandlerError("El efectivo recibido no cubre el total definitivo del pedido.", "DATOS_INVALIDOS")

    payment = Pago(
        id_pedido=order.id_pedido, metodo_pago=method, monto=amount,
        estado="PENDIENTE", idempotency_key=operation_uuid,
        currency=settings.stripe_currency.upper(), cash_received=received,
        cash_change=(received - amount).quantize(Decimal("0.01")) if received is not None else Decimal("0.00"),
    )
    db.add(payment)
    if method == "EFECTIVO" and received is not None:
        try:
            consume_order_stock(db, order)
        except Exception as error:
            raise SyncHandlerError("No se pudo conciliar el efectivo por falta de inventario.",
                                   "CONFLICTO_INVENTARIO", result={"requires_refund_review": True}) from error
        payment.estado = "PAGADO"
        payment.fecha_pago = datetime.now(timezone.utc)
        order.estado = "CONFIRMADO"
    AuditService.record(db, organization_id=actor.organization_id, actor_id=actor.user_id,
        actor_role=actor.role, action="SOLICITUD_PAGO_OFFLINE_REGISTRADA", entity="Pago",
        entity_id=None, result=payment.estado,
        details={"id_pedido": order.id_pedido, "metodo_pago": method,
                 "importe_servidor": str(amount), "estado": payment.estado},
        dedupe_key=f"offline-payment:{actor.organization_id}:{operation_uuid}")
    db.flush([payment])
    return _result(payment, requires_online=method in {"TARJETA", "QR"})


def _result(payment: Pago, *, requires_online: bool) -> dict[str, Any]:
    return {"id_pago": payment.id_pago, "id_pedido": payment.id_pedido,
            "metodo_pago": payment.metodo_pago, "monto": str(payment.monto),
            "currency": payment.currency, "estado": payment.estado,
            "simulated": payment.simulated,
            "cash_received": str(payment.cash_received) if payment.cash_received is not None else None,
            "cash_change": str(payment.cash_change),
            "requires_online_confirmation": requires_online}


def register_payment_handlers(registry: SyncHandlerRegistry) -> None:
    registry.register("pago.solicitar", request_offline_payment)
