"""MCPServer assembly: context, guard-filtered tool registration, resources,
audit wrapping, and `server/discover` identity."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.tools.base import ToolError

from . import __version__, prompts, resources, tools
from .client.http import StudioClient
from .context import AppContext
from .policy.audit import AuditLogger
from .policy.guard import ToolGuard
from .policy.ratelimit import TokenBucketLimiter
from .protocol.discovery import build_identity
from .settings import Settings

logger = logging.getLogger(__name__)


class AuditedMCP:
    """Wraps MCPServer.tool() to record every call in the audit log.

    Credential-like argument values (password/token/pat/secret) are masked
    before persisting — the audit log must never become a credential leak.
    """

    _SENSITIVE_KEY_PARTS = ("password", "token", "pat", "secret")

    def __init__(self, mcp: MCPServer, ctx: AppContext):
        self._mcp = mcp
        self._ctx = ctx

    @classmethod
    def _mask(cls, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            k: ("***" if any(p in k.lower() for p in cls._SENSITIVE_KEY_PARTS) else v)
            for k, v in arguments.items()
        }

    def tool(self, *, name: str, description: str, **kwargs: Any):
        real_decorator = self._mcp.tool(name=name, description=description, **kwargs)

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)  # preserve signature → SDK builds the right arg model
            async def audited_fn(*args: Any, **call_args: Any) -> Any:
                limiter = self._ctx.rate_limiter
                identity = self._identity()
                if limiter is not None and not limiter.acquire(identity or "default"):
                    wait = limiter.retry_after_seconds(identity or "default")
                    raise ToolError(
                        f"调用过于频繁，已触发限流（{limiter.per_minute} 次/分钟）；"
                        f"约 {max(wait, 0.1):.0f} 秒后可重试"
                    )
                start = time.monotonic()
                result_state = "ok"
                try:
                    return await fn(*args, **call_args)
                except Exception as exc:
                    result_state = f"error:{type(exc).__name__}"
                    raise
                finally:
                    duration_ms = (time.monotonic() - start) * 1000
                    try:
                        self._ctx.audit.record(
                            tool=name,
                            arguments=self._mask({k: v for k, v in call_args.items()}),
                            result=result_state,
                            duration_ms=duration_ms,
                            identity=self._identity(),
                        )
                    except Exception as audit_exc:  # audit must never break a call
                        logger.warning("audit record failed for %s: %s", name, audit_exc)

            return real_decorator(audited_fn)

        return decorator

    def _identity(self) -> str | None:
        s = self._ctx.settings
        return s.username or (s.auth_mode if s.auth_mode != "password" else None)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._mcp, item)


def build_server(
    settings: Settings,
    *,
    transport: Any | None = None,
    version: str = __version__,
) -> tuple[MCPServer, AppContext]:
    """Build the MCPServer + its AppContext. Caller runs it (stdio/http)."""
    client = StudioClient(settings, transport=transport)
    guard = ToolGuard(settings)
    audit = AuditLogger(settings.audit_file)
    identity = build_identity(version, settings.version_list)
    ctx = AppContext(
        settings=settings,
        client=client,
        guard=guard,
        audit=audit,
        rate_limiter=TokenBucketLimiter(settings.rate_limit_per_minute),
        protocol_identity=identity.to_dict(),
    )

    mcp = MCPServer(
        name="studiosystem-mcp",
        title="Studio System MCP",
        description=(
            "Studio System 的 MCP 适配层：用例导图（读为文本大纲）、任务、Wiki 文档。"
            "写操作带两阶段确认；错误归一化为可读中文提示。"
        ),
        version=version,
        instructions=(
            "用 studio_status 确认连通性与身份；用 studio_capabilities 查看当前可用工具。"
            "读导图优先 case_get_map（文本大纲），不要请求原始 JSON。"
            "所有 id 从 list 工具获取，不要臆造。写工具（P1 起）默认先 dry_run 看 diff。"
        ),
    )

    audited = AuditedMCP(mcp, ctx)
    tools.register_tools(audited, ctx)
    resources.register_resources(audited, ctx)
    prompts.register(audited, ctx)

    # Spec (§6.9): tools/list must be deterministically sorted. The SDK returns
    # registration order, so wrap list_tools — _handle_list_tools calls it.
    orig_list_tools = mcp.list_tools

    async def sorted_list_tools():
        result = await orig_list_tools()
        result.sort(key=lambda t: t.name)
        return result

    mcp.list_tools = sorted_list_tools  # type: ignore[method-assign]

    logger.info(
        "studiosystem-mcp %s ready: modules=%s tools=%s transport=%s",
        version,
        sorted(settings.enabled_modules),
        guard.registered_tools(),
        settings.transport,
    )
    return mcp, ctx
