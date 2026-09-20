"""Payment provider adapters.

Stripe is the only card provider implemented here.  QR deliberately remains an
explicitly unconfigured provider until a real bank/acquirer integration is
available; the API never fabricates a QR code or marks a payment as paid.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.core.config import settings


class PaymentProviderError(RuntimeError):
    pass


class StripeCardPaymentProvider:
    def __init__(self) -> None:
        if not settings.stripe_secret_key:
            raise PaymentProviderError("Stripe no está configurado actualmente")
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise PaymentProviderError("La dependencia de Stripe no está instalada") from exc
        self.stripe = stripe
        self.stripe.api_key = settings.stripe_secret_key

    @staticmethod
    def amount_in_minor_units(amount: Decimal) -> int:
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def create_intent(self, amount: Decimal, id_pedido: int) -> dict[str, Any]:
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=self.amount_in_minor_units(amount),
                currency=settings.stripe_currency.lower(),
                automatic_payment_methods={"enabled": True},
                metadata={"id_pedido": str(id_pedido)},
                idempotency_key=f"pedido-{id_pedido}",
            )
        except Exception as exc:
            raise PaymentProviderError("No se pudo crear el intento de pago en Stripe") from exc
        return {"id": intent.id, "client_secret": intent.client_secret, "status": intent.status}

    def retrieve_intent(self, reference: str) -> dict[str, Any]:
        try:
            intent = self.stripe.PaymentIntent.retrieve(reference)
        except Exception as exc:
            raise PaymentProviderError("No se pudo recuperar el intento de pago") from exc
        return {"id": intent.id, "client_secret": intent.client_secret, "status": intent.status}


class QRPaymentProvider:
    configured = False

    @classmethod
    def unavailable_message(cls) -> str:
        return "Pago QR no configurado actualmente."


class CashPaymentProvider:
    @staticmethod
    def initial_status() -> str:
        return "PENDIENTE"
