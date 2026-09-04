from typing import Any, Protocol


class ReportCache(Protocol):
    """Contract for a future cache backend such as Redis."""

    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...
