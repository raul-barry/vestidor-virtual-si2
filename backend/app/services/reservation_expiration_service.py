"""Atomically expire unpaid, uncompleted reservations and release held stock."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.inventario import Inventario
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.models.pedido import Pedido
from app.models.pago import Pago
from app.services.audit_service import AuditService


ACTIVE_RESERVATION_STATES = ("PENDIENTE", "RESERVADA", "CONFIRMADA")


class ReservationExpirationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def process_expired(self, *, now: datetime | None = None, batch_size: int = 500) -> dict[str, int]:
        """Expire one bounded batch. Row locks and state transition make retries safe."""
        if not 1 <= batch_size <= 5000:
            raise ValueError("batch_size debe estar entre 1 y 5000")
        self.db.info.pop("organization_id", None)
        instant = self._utc(now or datetime.now(timezone.utc))
        candidates = self.db.scalars(
            select(Reserva)
            .where(
                Reserva.estado.in_(ACTIVE_RESERVATION_STATES),
                Reserva.fecha_expiracion.is_not(None),
                Reserva.fecha_expiracion <= instant,
            )
            .order_by(Reserva.fecha_expiracion, Reserva.id_reserva)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        ).all()

        expired = 0
        inconsistent_inventory = 0
        for reservation in candidates:
            # Re-check after taking the reservation lock; another worker may have
            # completed or cancelled it while this worker waited.
            if reservation.estado not in ACTIVE_RESERVATION_STATES:
                continue
            order = payment = None
            if reservation.id_pedido is not None:
                order = self.db.scalar(select(Pedido).where(
                    Pedido.id_pedido == reservation.id_pedido
                ).with_for_update())
                payment = self.db.scalar(select(Pago).where(
                    Pago.id_pedido == reservation.id_pedido
                ).with_for_update())
                if (order is None or order.estado not in {"PENDIENTE", "CANCELADO"}
                        or payment is None or payment.estado == "PAGADO"):
                    continue
            inventory = self.db.scalar(
                select(Inventario)
                .where(Inventario.id_inventario == reservation.id_inventario)
                .with_for_update()
            )
            if inventory is None or inventory.stock_reservado < reservation.cantidad:
                inconsistent_inventory += 1
                continue

            user = self.db.get(Usuario, reservation.id_usuario)
            if user is None:
                inconsistent_inventory += 1
                continue

            inventory.stock_reservado -= reservation.cantidad
            inventory.stock_disponible += reservation.cantidad
            previous_state = reservation.estado
            reservation.estado = "EXPIRADA"
            if order is not None and payment is not None:
                payment.estado = "CANCELADO"
                order.estado = "CANCELADO"
            AuditService.record(
                self.db,
                organization_id=user.id_organizacion,
                actor_id=None,
                actor_role="SISTEMA",
                action="RESERVA_VENCIDA",
                entity="Reserva",
                entity_id=reservation.id_reserva,
                details={
                    "estado_anterior": previous_state,
                    "estado_nuevo": "EXPIRADA",
                    "id_inventario": inventory.id_inventario,
                    "cantidad_liberada": reservation.cantidad,
                    "id_pedido": reservation.id_pedido,
                },
                dedupe_key=f"reservation-expiration:{reservation.id_reserva}",
            )
            expired += 1

        if expired:
            self.db.commit()
        else:
            self.db.rollback()
        return {"expiradas": expired, "inconsistencias_inventario": inconsistent_inventory}

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
