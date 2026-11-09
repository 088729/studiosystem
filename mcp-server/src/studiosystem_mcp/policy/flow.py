"""Two-phase write confirmation flow shared by all write tools.

Risk-tiered (Q4):
- `force=True` tools (整树覆盖类: case_edit_map / rollback / purge …) always
  require confirmation unless STUDIO_MCP_CONFIRM_MODE=none.
- Low-risk tools (task_create 等) execute in one step by default; pass
  dry_run=true to preview.

Token channel (P0): without `confirm_token`, the tool returns the preview +
a single-use 5-minute token; re-invoking with the token executes with the
originally validated arguments. P2 adds protocol-native elicitation / MRTR.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from ..errors import StudioError

if TYPE_CHECKING:
    from ..context import AppContext

CONFIRM_HINT = "确认无误后，用相同参数再次调用并传入 confirm_token 执行写入"


def pop_flow_args(arguments: dict[str, Any]) -> tuple[str | None, bool]:
    """Extract and remove flow-control args from tool arguments."""
    token = arguments.pop("confirm_token", None)
    dry_run = bool(arguments.pop("dry_run", False))
    return token, dry_run


async def confirm_gate(
    ctx: AppContext,
    tool: str,
    arguments: dict[str, Any],
    preview: dict[str, Any],
    execute: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    *,
    force: bool,
) -> dict[str, Any]:
    """Decide preview/execute based on confirm_mode and the presented token."""
    token, dry_run = pop_flow_args(arguments)
    mode = ctx.settings.confirm_mode

    if token:
        pending = ctx.confirm.consume(token, tool)
        if pending is None:
            return {
                "ok": False,
                "code": "confirm_token_invalid",
                "message": "confirm_token 无效、已使用或已过期（5 分钟有效，单次使用）",
                "hint": "请重新调用本工具获取新的确认令牌",
            }
        # execute with the originally validated arguments, not the caller's
        return await execute(dict(pending.arguments))

    if dry_run:
        return {"ok": True, "dry_run": True, "preview": preview}

    if force and mode != "none":
        issued = ctx.confirm.issue(tool, dict(arguments), preview)
        return {
            "ok": True,
            "requires_confirmation": True,
            "confirm_token": issued,
            "preview": preview,
            "hint": CONFIRM_HINT,
        }

    return await execute(dict(arguments))


def err_dict(exc: StudioError) -> dict[str, Any]:
    return exc.to_dict()
