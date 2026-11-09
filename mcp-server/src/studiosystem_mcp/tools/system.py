"""System-domain tools: status, capabilities, whoami (permission self-check)."""

from __future__ import annotations

import logging

import httpx

from ..context import AppContext
from ..errors import StudioError

logger = logging.getLogger(__name__)


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="studio_status",
        description=(
            "检查与 Studio 后端的连通性，返回后端地址、当前身份（用户名/角色/权限集）与后端健康状态。"
            "任何操作前可先用它确认凭据有效。"
        ),
    )
    async def studio_status() -> dict:
        identity = None
        health = None
        try:
            # /health lives outside /api/v1 — use an absolute URL
            resp = await ctx.client._client.get(f"{s.studio_base_url}/health", follow_redirects=False)
            health = {"reachable": resp.status_code == 200, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            health = {"reachable": False, "error": str(exc)}
        try:
            me = await ctx.client.get("/common/auth/me")
            identity = {
                "username": me.get("username"),
                "role_name": me.get("role_name"),
                "permissions": me.get("perms", []),
            }
        except StudioError as exc:
            identity = {"error": exc.message, "code": exc.code}
        return {
            "ok": bool(health.get("reachable")),
            "backend": s.studio_base_url,
            "auth_mode": s.auth_mode,
            "health": health,
            "identity": identity,
        }

    @mcp.tool(
        name="studio_capabilities",
        description=(
            "返回当前 MCP server 的配置摘要（已脱敏）：启用的能力域、已注册工具、只读状态、"
            "确认策略、协议版本。用于判断「我现在能做什么」。"
        ),
    )
    async def studio_capabilities() -> dict:
        return {
            "ok": True,
            "server": "studiosystem-mcp",
            "protocol": ctx.protocol_identity,
            "protocol_versions": s.version_list,
            "enabled_modules": sorted(s.enabled_modules),
            "read_only": s.read_only,
            "confirm_mode": s.confirm_mode,
            "allow_destructive": s.allow_destructive,
            "registered_tools": ctx.guard.visible_summary(),
            "config": s.redacted(),
        }

    @mcp.tool(
        name="whoami",
        description=(
            "权限自检：返回当前凭据对应的用户、角色与完整权限键列表。"
            "写操作 403 时先调用它确认缺哪个权限键。"
        ),
    )
    async def whoami() -> dict:
        me = await ctx.client.get("/common/auth/me")
        return {
            "ok": True,
            "username": me.get("username"),
            "role_name": me.get("role_name"),
            "permissions": me.get("perms", []),
            "full_name": me.get("full_name"),
            "department": me.get("department"),
            "job_scope": me.get("job_scope"),
        }
