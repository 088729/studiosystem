"""Shared application context: settings, HTTP client, guard, audit, confirm store."""

from __future__ import annotations

from dataclasses import dataclass, field

from .client.http import StudioClient
from .client.idempotency import MemoryIdempotencyStore
from .policy.audit import AuditLogger
from .policy.confirm import ConfirmTokenStore
from .policy.guard import ToolGuard
from .policy.ratelimit import TokenBucketLimiter
from .settings import Settings


@dataclass
class AppContext:
    settings: Settings
    client: StudioClient
    guard: ToolGuard
    audit: AuditLogger
    confirm: ConfirmTokenStore = field(default_factory=ConfirmTokenStore)
    idempotency: MemoryIdempotencyStore = field(default_factory=MemoryIdempotencyStore)
    rate_limiter: TokenBucketLimiter | None = None
    protocol_identity: dict = field(default_factory=dict)  # server/discover identity

    async def aclose(self) -> None:
        await self.client.aclose()
        self.audit.close()
