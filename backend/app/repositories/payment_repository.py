from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.cliente import Cliente


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_payment(self, id_pedido: int, metodo_pago: str, monto: Decimal) -> Pago:
        payment = Pago(id_pedido=id_pedido, metodo_pago=metodo_pago, monto=monto, estado="PENDIENTE")
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def get_payment_by_order(self, id_pedido: int) -> Pago | None:
        statement = select(Pago).where(Pago.id_pedido == id_pedido)
        return self.db.scalar(statement)

    def get_payment_by_id(self, id_pago: int) -> Pago | None:
        return self.db.get(Pago, id_pago)

    def get_order_by_id(self, id_pedido: int) -> Pedido | None:
        return self.db.get(Pedido, id_pedido)

    def get_client_by_user(self, id_usuario: int) -> Cliente | None:
        statement = select(Cliente).where(Cliente.id_usuario == id_usuario)
        return self.db.scalar(statement)

    def update_payment_status(self, payment: Pago, estado: str) -> Pago:
        payment.estado = estado
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def update_order_status(self, order: Pedido, estado: str) -> Pedido:
        order.estado = estado
        self.db.flush()
        self.db.refresh(order)
        return order
