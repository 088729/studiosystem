"""P1 read-only extensions: analytics / focus / habits domains."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(modules="case,task,wiki,analytics,focus,habits", audit_file=str(tmp_path / "audit.jsonl")),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestAnalytics:
    async def test_task_overview(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("task_overview", {})).content[0].text)
        assert payload["overview"]["overdue"] == 2
        assert payload["overview"]["completed_total"] == 42

    async def test_summary_markdown(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_summary_markdown", {"range": "this_week"})).content[0].text
        )
        assert "# 本周摘要" in payload["markdown"]
        assert payload["total"] == 3

    async def test_summary_bad_backend_kind(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("focus_report", {"kind": "breakdown", "by": "tag"})).content[0].text)
        assert payload["kind"] == "breakdown"
        assert payload["data"]["rows"][0]["seconds"] == 3600


class TestFocus:
    async def test_focus_status_idle(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("focus_status", {})).content[0].text)
        assert payload["running"] is False and payload["session"] is None

    async def test_focus_report_default(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("focus_report", {})).content[0].text)
        assert payload["overview"]["total_seconds"] == 7500
        assert payload["breakdown"]["kind"] == "breakdown"

    async def test_focus_report_invalid_kind(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("focus_report", {"kind": "nope"})
        msg = str(ei.value)
        assert "trend" in msg and "heatmap" in msg


class TestHabits:
    async def test_habit_today(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("habit_today", {})).content[0].text)
        assert payload["count"] == 2
        assert payload["unchecked_names"] == ["阅读"]

    async def test_habit_week(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("habit_week", {})).content[0].text)
        assert payload["days"][0]["date"] == "2026-11-03"

    async def test_habit_stats(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("habit_stats", {"habit_id": "h1", "month": "2026-11"})).content[0].text)
        assert payload["stats"]["best_streak"] == 12


class TestModuleGating:
    async def test_focus_domain_off_by_default(self, mock_transport):
        mcp, ctx = build_server(make_settings(), transport=mock_transport)  # modules=case,task,wiki
        try:
            tools = {t.name for t in await mcp.list_tools()}
            assert "focus_status" not in tools
            assert "habit_today" not in tools
            assert "task_overview" not in tools
            assert "case_edit_map" in tools  # write tools of core domains registered
        finally:
            await ctx.aclose()

    async def test_read_only_mode_removes_all_writes(self, mock_transport):
        mcp, ctx = build_server(make_settings(read_only=True), transport=mock_transport)
        try:
            tools = {t.name for t in await mcp.list_tools()}
            assert "case_edit_map" not in tools
            assert "task_create" not in tools
            assert "case_get_map" in tools
            assert "whoami" in tools
        finally:
            await ctx.aclose()
