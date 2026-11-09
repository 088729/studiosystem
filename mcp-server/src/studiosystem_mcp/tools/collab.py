"""Collab domain (P2): comments / calendar range / reminders / share members.

All tools here are low-risk and reversible, so they execute in one step
(dry_run still available for previews).
"""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import case as case_ad
from ..adapters import task as task_ad
from ..context import AppContext
from ..policy.flow import confirm_gate


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="task_comment",
        description=(
            "任务评论。action=list 查看评论列表 / add 添加评论（一步执行）。"
            "评论对共享清单成员可见，注意措辞。"
        ),
    )
    async def task_comment(
        task_id: str,
        action: str = "list",
        content: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if action == "list":
                data = await ctx.client.get(f"/task/tasks/{task_id}/comments")
                items = data.get("items", [])
                return {"ok": True, "task_id": task_id, "count": len(items), "comments": items}
            if action == "add":
                if not content:
                    raise ToolError("action=add 需要 content 参数")
                preview = {"task_id": task_id, "action": "add", "content_chars": len(content)}

                async def execute(_args: dict) -> dict:
                    comment = await ctx.client.post(
                        f"/task/tasks/{task_id}/comments", json={"content": content}
                    )
                    return {"ok": True, "task_id": task_id, "comment": comment}

                return await confirm_gate(
                    ctx, "task_comment", {"dry_run": dry_run}, preview, execute, force=False
                )
            raise ToolError(f"未知 action: {action}（可用 list/add）")
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="calendar_range",
        description=(
            "日历区间查询（含 todo+done，子任务不上日历）。start/end 为 ISO 时间；"
            "结果按 STUDIO_MCP_MAX_RESULT_ITEMS 裁剪并返回 has_more。"
        ),
    )
    async def calendar_range(
        start: str,
        end: str,
        limit: int | None = None,
    ) -> dict:
        try:
            data = await ctx.client.get(
                "/task/views/calendar", params={"start": start, "end": end}
            )
            items = data.get("items", []) if isinstance(data, dict) else (data or [])
            kept, has_more = case_ad.trim_items(items, limit or s.max_result_items)
            return {
                "ok": True,
                "start": start,
                "end": end,
                "count": len(kept),
                "total": len(items),
                "has_more": has_more,
                "tasks": [task_ad.format_task_line(t) for t in kept],
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="pending_reminders",
        description="待处理的提醒：到期未确认的任务提醒（含持续提醒与多个提醒时刻）。",
    )
    async def pending_reminders() -> dict:
        try:
            data = await ctx.client.get("/task/views/pending-reminders")
            items = data.get("items", [])
            return {"ok": True, "count": len(items), "reminders": items}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="reminder_ack",
        description="确认任务提醒：不再提醒；snooze_minutes 传入则推迟指定分钟数后再提醒。",
    )
    async def reminder_ack(task_id: str, snooze_minutes: int | None = None) -> dict:
        try:
            body = {} if snooze_minutes is None else {"snooze_minutes": snooze_minutes}
            await ctx.client.post(f"/task/tasks/{task_id}/reminders/ack", json=body)
            return {"ok": True, "task_id": task_id, "snoozed": snooze_minutes is not None}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="share_members",
        description=(
            "共享清单成员。action=list 查看成员 / add 添加成员（username + role=viewer|editor，一步执行）。"
        ),
    )
    async def share_members(
        list_id: str,
        action: str = "list",
        username: str | None = None,
        role: str = "viewer",
        dry_run: bool = False,
    ) -> dict:
        try:
            if action == "list":
                data = await ctx.client.get(f"/task/share/lists/{list_id}/members")
                items = data.get("items", [])
                return {"ok": True, "list_id": list_id, "count": len(items), "members": items}
            if action == "add":
                if not username:
                    raise ToolError("action=add 需要 username 参数")
                if role not in ("viewer", "editor"):
                    raise ToolError("role 必须是 viewer 或 editor")
                preview = {"list_id": list_id, "action": "add", "username": username, "role": role}

                async def execute(_args: dict) -> dict:
                    data = await ctx.client.post(
                        f"/task/share/lists/{list_id}/members", json={"username": username, "role": role}
                    )
                    return {"ok": True, "list_id": list_id, "members": data.get("items", [])}

                return await confirm_gate(
                    ctx, "share_members", {"dry_run": dry_run}, preview, execute, force=False
                )
            raise ToolError(f"未知 action: {action}（可用 list/add）")
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc
