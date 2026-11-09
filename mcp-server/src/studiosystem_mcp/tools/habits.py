"""Habits tools: read (P1) + checkin/skip/uncheckin (P2)."""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..context import AppContext
from ..policy.flow import confirm_gate


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="habit_today",
        description=(
            "习惯打卡今日视图：每个习惯的达标状态/连续天数(streak)/今日次数/周位图。"
            "date 可回看指定日期（YYYY-MM-DD）。晨报「今天还有哪些没打」用它。"
        ),
    )
    async def habit_today(date: str | None = None) -> dict:
        try:
            params: dict = {"tz_offset_minutes": s.tz_offset_minutes}
            if date:
                params["date"] = date
            data = await ctx.client.get("/task/habits", params=params)
            items = data.get("items", [])
            unchecked = [h["name"] for h in items if not h.get("today_checked") and not h.get("today_skipped")]
            return {
                "ok": True,
                "date": date or "今天",
                "count": len(items),
                "habits": items,
                "unchecked_names": unchecked,
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="habit_week",
        description="本周概览：周一到周日每天达标习惯数/总数（周环条数据）。",
    )
    async def habit_week() -> dict:
        try:
            data = await ctx.client.get("/task/habits/week", params={"tz_offset_minutes": s.tz_offset_minutes})
            return {"ok": True, "days": data.get("days", [])}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="habit_stats",
        description="单个习惯详情：四卡统计 + 月历打卡表 + 月度概览（month 格式 YYYY-MM）。",
    )
    async def habit_stats(habit_id: str, month: str | None = None) -> dict:
        try:
            params: dict = {"tz_offset_minutes": s.tz_offset_minutes}
            if month:
                params["month"] = month
            data = await ctx.client.get(f"/task/habits/{habit_id}/stats", params=params)
            return {"ok": True, "habit_id": habit_id, "stats": data}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- write tools (P2) ----------------

    @mcp.tool(
        name="habit_checkin",
        description=(
            "习惯打卡（一步执行）。date 缺省按服务时区算今天（YYYY-MM-DD）；amount 手动计量模式的本次完成量；"
            "mood 1-5 心情；meta_only=true 只写心情/日志不增加次数。"
        ),
    )
    async def habit_checkin(
        habit_id: str,
        date: str | None = None,
        amount: int | None = None,
        note: str | None = None,
        mood: int | None = None,
        meta_only: bool = False,
        dry_run: bool = False,
    ) -> dict:
        try:
            body: dict = {"meta_only": meta_only}
            if date:
                body["date"] = date
            if amount is not None:
                if not 1 <= amount <= 999:
                    raise ToolError("amount 必须在 1-999 之间")
                body["amount"] = amount
            if note:
                body["note"] = note
            if mood is not None:
                if not 1 <= mood <= 5:
                    raise ToolError("mood 必须在 1-5 之间")
                body["mood"] = mood
            preview = {"habit_id": habit_id, **body}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(
                    f"/task/habits/{habit_id}/checkin",
                    json=body,
                    params={"tz_offset_minutes": s.tz_offset_minutes},
                )
                return {"ok": True, "habit_id": habit_id, "result": result}

            return await confirm_gate(
                ctx, "habit_checkin", {"dry_run": dry_run}, preview, execute, force=False
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="habit_skip",
        description="跳过某日打卡（不算打卡也不打断 streak；当日已达标会报错）。date 缺省为今天。",
    )
    async def habit_skip(habit_id: str, date: str | None = None, dry_run: bool = False) -> dict:
        try:
            body = {} if not date else {"date": date}
            preview = {"habit_id": habit_id, "action": "skip", **body}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(
                    f"/task/habits/{habit_id}/skip",
                    json=body,
                    params={"tz_offset_minutes": s.tz_offset_minutes},
                )
                return {"ok": True, "habit_id": habit_id, "result": result}

            return await confirm_gate(
                ctx, "habit_skip", {"dry_run": dry_run}, preview, execute, force=False
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="habit_un_checkin",
        description="撤销某日打卡（删除当日打卡记录）。date 缺省为今天；只读操作不可撤销，请确认日期。",
    )
    async def habit_un_checkin(habit_id: str, date: str | None = None, dry_run: bool = False) -> dict:
        try:
            params = {"tz_offset_minutes": s.tz_offset_minutes}
            if date:
                params["date"] = date
            preview = {"habit_id": habit_id, "action": "uncheckin", "date": date or "今天"}

            async def execute(_args: dict) -> dict:
                await ctx.client.delete(f"/task/habits/{habit_id}/checkin", params=params)
                return {"ok": True, "habit_id": habit_id, "undone": True, "date": date or "今天"}

            return await confirm_gate(
                ctx, "habit_un_checkin", {"dry_run": dry_run}, preview, execute, force=False
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc
