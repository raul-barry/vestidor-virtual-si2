from decimal import Decimal

import pytest

from app.core.exceptions import AppException
from app.models.cliente import Cliente
from app.models.pedido import Pedido
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.payment import CreatePaymentRequest
from app.services.payment_service import PaymentService


def create_order(db) -> Pedido:
    role = Rol(nombre="CLIENTE", descripcion=None)
    usuario = Usuario(
        rol=role,
        nombres="Carlos",
        apellidos="Perez",
        correo="cliente@example.com",
        telefono="70000000",
        password_hash="hash",
    )
    cliente = Cliente(usuario=usuario)
    order = Pedido(cliente=cliente, estado="PENDIENTE", total=Decimal("500.00"))
    db.add_all([role, usuario, cliente, order])
    db.commit()
    return order


def test_create_payment_uses_order_total(db) -> None:
    order = create_order(db)

    payment = PaymentService(db).create_payment(
        CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="QR")
    )

    assert payment.id_pedido == order.id_pedido
    assert payment.metodo_pago == "QR"
    assert payment.monto == Decimal("500.00")
    assert payment.estado == "PENDIENTE"


def test_create_payment_rejects_duplicate_order_payment(db) -> None:
    order = create_order(db)
    service = PaymentService(db)
    service.create_payment(CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="EFECTIVO"))

    with pytest.raises(AppException, match="El pedido ya tiene un pago creado"):
        service.create_payment(CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="QR"))


def test_approve_payment_confirms_order(db) -> None:
    order = create_order(db)
    service = PaymentService(db)
    payment = service.create_payment(CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="TARJETA"))

    approved_payment = service.approve_payment(payment.id_pago)

    assert approved_payment.estado == "PAGADO"
    db.refresh(order)
    assert order.estado == "CONFIRMADO"


def test_reject_payment_updates_payment_state_only(db) -> None:
    order = create_order(db)
    service = PaymentService(db)
    payment = service.create_payment(CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="EFECTIVO"))

    rejected_payment = service.reject_payment(payment.id_pago)

    assert rejected_payment.estado == "FALLIDO"
    db.refresh(order)
    assert order.estado == "PENDIENTE"


def test_stripe_success_can_follow_a_failed_attempt(db) -> None:
    order = create_order(db)
    service = PaymentService(db)
    payment = service.create_payment(CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="TARJETA"))

    service.reject_payment(payment.id_pago)
    approved_payment = service.approve_payment(payment.id_pago, allow_retry_from_failed=True)

    assert approved_payment.estado == "PAGADO"
    db.refresh(order)
    assert order.estado == "CONFIRMADO"
