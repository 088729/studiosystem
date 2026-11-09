"""Client-side idempotency: key → cached result.

The backend has no idempotency keys (§2), so repeated model-driven create
calls would duplicate objects. P0 ships the store; P1 wires it into write
tools (`Idempotency-Key` style: same tool args → same cached result).
"""

from __future__ import annotations

import time
from typing import Any, Protocol


class IdempotencyStore(Protocol):
    def get(self, key: str) -> Any | None: ...

    def put(self, key: str, value: Any, ttl_seconds: float) -> None: ...


class MemoryIdempotencyStore:
    """In-memory TTL cache (per-process). Optional file persistence comes in P1."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if time.monotonic() > expires_at:
            self._data.pop(key, None)
            return None
        return value

    def put(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._data[key] = (time.monotonic() + ttl_seconds, value)

    def __len__(self) -> int:  # pragma: no cover - debugging aid
        return len(self._data)
