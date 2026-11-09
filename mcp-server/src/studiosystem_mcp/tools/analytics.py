"""Analytics-domain read tools (P1): overview numbers + markdown summary (日报/周报素材)."""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..context import AppContext


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="task_overview",
        description=(
            "任务概览数字：今日待办（含逾期）、逾期数、已完成总数、按清单/智能清单的未完成聚合。"
            "与前端统计页同源（GET /task/views/summary）。"
        ),
    )
    async def task_overview() -> dict:
        try:
            data = await ctx.client.get("/task/views/summary", params={"tz_offset_minutes": s.tz_offset_minutes})
            return {"ok": True, "overview": data}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_summary_markdown",
        description=(
            "任务周期摘要，直接返回 markdown 文本（生成 Wiki 周报的现成素材）。"
            "range: today/yesterday/this_week/last_week/this_month/custom；group_by: status/list。"
        ),
    )
    async def task_summary_markdown(
        range: str = "this_week",
        group_by: str = "status",
        list_ids: list[str] | None = None,
        tags: list[str] | None = None,
        statuses: list[str] | None = None,
    ) -> dict:
        try:
            payload: dict = {
                "range": range,
                "group_by": group_by,
                "tz_offset_minutes": s.tz_offset_minutes,
            }
            if list_ids:
                payload["list_ids"] = list_ids
            if tags:
                payload["tags"] = tags
            if statuses:
                payload["statuses"] = statuses
            data = await ctx.client.post("/task/summary/preview", json=payload)
            return {
                "ok": True,
                "range": range,
                "markdown": data.get("markdown", ""),
                "total": data.get("total"),
                "groups": data.get("groups"),
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc
