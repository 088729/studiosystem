"""Tool guard: module switches, read-only mode, allow/deny lists.

Applied at registration time — filtered-out tools simply never appear in
`tools/list`, which keeps the model's choice space small (§6.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..settings import Settings


@dataclass(frozen=True)
class ToolMeta:
    """Registration-time metadata for one tool."""

    name: str
    domain: str  # case | task | wiki | system | focus | ...
    read_only: bool
    destructive: bool = False  # purge / hard delete / rollback / push


class ToolGuard:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._metas: dict[str, ToolMeta] = {}

    def register(self, meta: ToolMeta) -> bool:
        """Decide whether a tool should be registered; record its meta."""
        s = self._settings
        if meta.domain != "system" and meta.domain not in s.enabled_modules:
            return False
        if s.read_only and not meta.read_only:
            return False
        if meta.name in s.denied_tool_set:
            return False
        allowed = s.allowed_tool_set
        if allowed is not None and meta.name not in allowed:
            return False
        if meta.destructive and not s.allow_destructive:
            return False
        self._metas[meta.name] = meta
        return True

    def is_registered(self, name: str) -> bool:
        return name in self._metas

    def registered_tools(self) -> list[str]:
        return sorted(self._metas)

    def visible_summary(self) -> dict[str, dict[str, object]]:
        return {
            name: {"domain": m.domain, "read_only": m.read_only, "destructive": m.destructive}
            for name, m in sorted(self._metas.items())
        }


def build_guard(settings: Settings) -> ToolGuard:
    return ToolGuard(settings)
