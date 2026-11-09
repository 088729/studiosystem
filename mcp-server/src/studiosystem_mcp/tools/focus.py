"""Focus (pomodoro) tools: read (P1) + session control (P2)."""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..context import AppContext
from ..policy.flow import confirm_gate

_VALID_KINDS = {"trend", "hours", "heatmap", "timeline", "breakdown"}


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="focus_status",
        description="当前是否有进行中的专注会话（含已暂停），有则返回会话详情（任务/计划时长/实际秒数）。",
    )
    async def focus_status() -> dict:
        try:
            data = await ctx.client.get("/task/focus", params={"running_only": True})
            items = data.get("items", [])
            return {"ok": True, "running": bool(items), "session": items[0] if items else None}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="focus_report",
        description=(
            "专注统计。默认返回概览 + 本周按任务占比排行；"
            "kind: trend(趋势)/hours(24h分布)/heatmap(年度热力)/timeline(周矩阵)/breakdown(占比，by=task/list/tag)。"
            "输出适合直接写进日报/复盘。"
        ),
    )
    async def focus_report(
        kind: str | None = None,
        by: str = "task",
        period: str = "week",
        date: str | None = None,
        month: str | None = None,
        year: str | None = None,
        week_start: str | None = None,
    ) -> dict:
        try:
            base = {"tz_offset_minutes": s.tz_offset_minutes}
            if kind is None:
                overview = await ctx.client.get("/task/focus/stats", params=base)
                breakdown = await ctx.client.get(
                    "/task/focus/stats/detail", params={**base, "kind": "breakdown", "by": by, "period": period}
                )
                return {"ok": True, "overview": overview, "breakdown": breakdown}
            if kind not in _VALID_KINDS:
                raise ToolError(f"未知 kind: {kind}（可用 {'/'.join(sorted(_VALID_KINDS))}）")
            params = {**base, "kind": kind}
            for key, val in (
                ("by", by),
                ("period", period),
                ("date", date),
                ("month", month),
                ("year", year),
                ("week_start", week_start),
            ):
                if val is not None:
                    params[key] = val
            data = await ctx.client.get("/task/focus/stats/detail", params=params)
            return {"ok": True, "kind": kind, "data": data}
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- write tools (P2) ----------------

    @mcp.tool(
        name="focus_start",
        description=(
            "开始专注会话（一步执行）。关联 task_id / habit_id 二选一或不关联；"
            "planned_minutes 默认 25。返回会话 id，后续 focus_pause/resume/finish/abandon 要用。"
            "已有进行中会话时后端会报错，可先 focus_status 确认。"
        ),
    )
    async def focus_start(
        task_id: str | None = None,
        planned_minutes: int = 25,
        preset_id: str | None = None,
        habit_id: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            body: dict = {"planned_minutes": planned_minutes}
            if task_id:
                body["task_id"] = task_id
            if preset_id:
                body["preset_id"] = preset_id
            if habit_id:
                body["habit_id"] = habit_id
            preview = {"action": "start", **body}

            async def execute(_args: dict) -> dict:
                session = await ctx.client.post("/task/focus", json=body)
                return {"ok": True, "session": session}

            return await confirm_gate(
                ctx, "focus_start", {"dry_run": dry_run}, preview, execute, force=False
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    def _session_action(name: str, action: str, desc: str) -> None:
        @mcp.tool(
            name=name,
            description=desc,
        )
        async def _impl(session_id: str) -> dict:
            try:
                session = await ctx.client.post(f"/task/focus/{session_id}/{action}")
                return {"ok": True, "session": session}
            except Exception as exc:
                raise ToolError(str(exc)) from exc

    _session_action(
        "focus_pause",
        "pause",
        "暂停专注会话（计时挂起，可 resume 继续）。session_id 来自 focus_start 或 focus_status。",
    )
    _session_action(
        "focus_resume",
        "resume",
        "恢复已暂停的专注会话。",
    )
    _session_action(
        "focus_finish",
        "finish",
        "正常结束专注会话（计入统计）。",
    )
    _session_action(
        "focus_abandon",
        "abandon",
        "放弃专注会话（不计入完成，保留记录）。",
    )
