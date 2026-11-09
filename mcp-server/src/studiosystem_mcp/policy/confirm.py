"""Two-phase write confirmation.

P0 implements the `confirm_token` channel: a write tool called without
`confirm_token` (or with `dry_run=true`) computes its effect and returns a
structured preview + a single-use token valid for 5 minutes; the client then
re-invokes with `confirm_token` to actually execute.

P1/P2 will add protocol-native channels (elicitation on 2025-11-25 clients,
MRTR `InputRequiredResult` on 2026-07-28 clients) selected automatically per
client capability (STUDIO_MCP_CONFIRM_MODE=auto).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PendingConfirmation:
    tool: str
    arguments: dict[str, Any]
    preview: dict[str, Any]
    expires_at: float
    used: bool = False


class ConfirmTokenStore:
    TOKEN_TTL_SECONDS = 300.0

    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}

    def issue(self, tool: str, arguments: dict[str, Any], preview: dict[str, Any]) -> str:
        token = f"cft_{secrets.token_urlsafe(24)}"
        self._pending[token] = PendingConfirmation(
            tool=tool,
            arguments=arguments,
            preview=preview,
            expires_at=time.monotonic() + self.TOKEN_TTL_SECONDS,
        )
        return token

    def consume(self, token: str, expected_tool: str) -> PendingConfirmation | None:
        """Validate + single-use consume. Returns None on any failure."""
        item = self._pending.get(token)
        if item is None or item.used or item.tool != expected_tool:
            return None
        if time.monotonic() > item.expires_at:
            self._pending.pop(token, None)
            return None
        item.used = True
        self._pending.pop(token, None)
        return item

    def pending_count(self) -> int:  # pragma: no cover - debugging aid
        return len(self._pending)
