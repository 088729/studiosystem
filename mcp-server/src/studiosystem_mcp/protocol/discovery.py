"""Protocol discovery & version negotiation.

The mcp SDK implements `server/discover` on the low-level server (declaring
MODERN_PROTOCOL_VERSIONS and runtime capabilities) and negotiates per-request
via `_meta`. This module builds our declared identity for the
`studio_capabilities` tool and picks the effective protocol version for a
client given what it advertises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProtocolIdentity:
    server_name: str
    server_version: str
    supported_versions: tuple[str, ...]
    capabilities: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "server": self.server_name,
            "version": self.server_version,
            "supported_versions": list(self.supported_versions),
            "capabilities": self.capabilities,
        }


def build_identity(server_version: str, settings_versions: list[str]) -> ProtocolIdentity:
    return ProtocolIdentity(
        server_name="studiosystem-mcp",
        server_version=server_version,
        supported_versions=tuple(settings_versions),
        capabilities={
            "tools": True,
            "resources": True,
            "prompts": True,  # P2: weekly_report / testcase_spec / retro / case_review / standup
            "subscriptions": False,  # deferred: 提醒桥接待后端 SSE 端点稳定后实现
            "tasks": False,  # deferred: 202 后台任务轮询暂用 wiki_reindex 状态查询
            "sampling": False,  # 无服务端采样需求
            "elicitation": False,  # P1 write tools 用 confirm_token 通道
        },
    )


def negotiate_version(
    client_versions: list[str] | None,
    supported: tuple[str, ...],
) -> str:
    """Pick the effective protocol version for a client.

    Client advertises versions in `server/discover` or `_meta`; we take the
    first of OUR preferences that the client also supports, else the client's
    first known version, else our baseline (last supported = 2025-11-25).
    """
    if not client_versions:
        return supported[0]
    client_set = set(client_versions)
    for v in supported:
        if v in client_set:
            return v
    # unknown client versions: fall back to the oldest baseline we support
    return supported[-1]
