"""JSONL audit log. Credentials and sensitive fields are masked; stdio mode
must keep stdout protocol-clean, so the default sink is stderr."""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, TextIO

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "token", "access_token", "pat", "mcp_token", "secret", "authorization"}


def _mask(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else _mask(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v) for v in value]
    return value


class AuditLogger:
    """Append-only audit sink. `file_path` set → file + stderr; else stderr only."""

    def __init__(self, file_path: str | None = None):
        self._stream: TextIO | None = None
        if file_path:
            try:
                self._stream = open(file_path, "a", encoding="utf-8")  # noqa: SIM115 - long-lived handle
            except OSError as exc:
                logger.warning("audit file %s 不可写，退回 stderr: %s", file_path, exc)

    def record(
        self,
        *,
        tool: str,
        arguments: dict[str, Any],
        result: str,
        duration_ms: float,
        identity: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "tool": tool,
            "args": _mask(arguments),
            "result": result,
            "duration_ms": round(duration_ms, 1),
        }
        if identity:
            entry["identity"] = identity
        if extra:
            entry.update(_mask(extra))
        line = json.dumps(entry, ensure_ascii=False)
        if self._stream:
            try:
                self._stream.write(line + "\n")
                self._stream.flush()
            except OSError as exc:
                logger.warning("audit write failed: %s", exc)
        print(line, file=sys.stderr)

    def close(self) -> None:
        if self._stream:
            self._stream.close()
            self._stream = None
