"""Payment provider adapters.

Stripe handles real card payments. QR is a Stripe-labelled demo flow: it
creates no real bank transfer and must never be enabled as a real provider.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

from app.core.config import settings


class PaymentProviderError(RuntimeError):
    pass


class StripeCardPaymentProvider:
    def __init__(self) -> None:
        if not settings.stripe_secret_key or not settings.stripe_publishable_key:
            raise PaymentProviderError("Stripe no está configurado actualmente.")
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


class SimulatedStripeCardPaymentProvider:
    """Stripe-shaped adapter used only by the local/demo payment flow."""

    @staticmethod
    def create_intent(amount: Decimal, id_pedido: int) -> dict[str, Any]:
        reference = f"pi_demo_{uuid4().hex}"
        return {
            "id": reference,
            "client_secret": f"{reference}_secret_demo",
            "status": "requires_payment_method",
        }

    @staticmethod
    def retrieve_intent(reference: str) -> dict[str, Any]:
        return {
            "id": reference,
            "client_secret": f"{reference}_secret_demo",
            "status": "requires_payment_method",
        }


class QRPaymentProvider:
    @staticmethod
    def create_demo_request(id_pedido: int, amount: Decimal, currency: str) -> dict[str, str]:
        # Deliberately a generic demo payload, not a bank transfer QR.
        reference = f"qr_stripe_demo_{uuid4().hex}"
        return {
            "reference": reference,
            "payload": f"STRIPE-DEMO-QR|REF={reference}|PEDIDO={id_pedido}|MONTO={amount:.2f}|MONEDA={currency.upper()}",
        }


class CashPaymentProvider:
    @staticmethod
    def initial_status() -> str:
        return "PENDIENTE"
