from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SyncActor:
    user_id: int
    organization_id: int
    role: str
    device_limited: bool = False
    device_client_id: str | None = None
    device_credential_id: int | None = None


class SyncHandlerError(Exception):
    def __init__(self, message: str, category: str, *, retryable: bool = False, result: dict[str, Any] | None = None):
        super().__init__(message)
        self.category = category
        self.retryable = retryable
        self.result = result or {}


SyncHandler = Callable[[Session, SyncActor, dict[str, Any]], dict[str, Any]]


class SyncHandlerRegistry:
    """Extensible registry. Commercial operations are intentionally unregistered here."""

    def __init__(self) -> None:
        self._handlers: dict[str, SyncHandler] = {}

    def register(self, operation_type: str, handler: SyncHandler) -> None:
        if operation_type in self._handlers:
            raise ValueError(f"Ya existe un handler para {operation_type}")
        self._handlers[operation_type] = handler

    def get(self, operation_type: str) -> SyncHandler | None:
        return self._handlers.get(operation_type)


sync_handlers = SyncHandlerRegistry()

# Registration is isolated to the permitted CU26 reservation operation types.
from app.services.reservation_sync_handler import register_reservation_handlers  # noqa: E402

register_reservation_handlers(sync_handlers)

from app.services.sale_sync_handler import register_sale_handlers  # noqa: E402

register_sale_handlers(sync_handlers)

from app.services.pos_sync_handler import register_pos_handlers  # noqa: E402

register_pos_handlers(sync_handlers)

from app.services.exchange_sync_handler import register_exchange_handlers  # noqa: E402

register_exchange_handlers(sync_handlers)

from app.services.payment_sync_handler import register_payment_handlers  # noqa: E402

register_payment_handlers(sync_handlers)
