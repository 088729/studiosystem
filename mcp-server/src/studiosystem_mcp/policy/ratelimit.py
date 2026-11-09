"""Token-bucket rate limiter (P3): protect the backend from model loop storms.

The backend has no rate limiting of its own; a misbehaving or looping model
could hammer it. This limiter caps tool calls per minute per identity at the
MCP boundary. `per_minute <= 0` disables it.

Burst capacity equals one full window (per_minute tokens), refilled linearly —
steady-state throughput is per_minute/60 calls per second.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucketLimiter:
    """Thread-safe token bucket keyed by caller identity."""

    def __init__(self, per_minute: int, *, clock: Callable[[], float] = time.monotonic):
        self.per_minute = per_minute
        self._rate = per_minute / 60.0  # tokens per second
        self._capacity = float(max(per_minute, 1))
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}  # key → (tokens, last_refill)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.per_minute > 0

    def acquire(self, key: str = "default") -> bool:
        """Take one token for `key`; False when the bucket is empty."""
        if not self.enabled:
            return True
        now = self._clock()
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True

    def retry_after_seconds(self, key: str = "default") -> float:
        """Seconds until `key` regains one token (for error messages)."""
        if not self.enabled:
            return 0.0
        now = self._clock()
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
        if tokens >= 1.0:
            return 0.0
        return (1.0 - tokens) / self._rate
