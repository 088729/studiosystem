"""P2 focus / habits write tests."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(audit_file=str(tmp_path / "audit.jsonl"), modules="task,focus,habits"),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestFocusWrite:
    async def test_start_returns_session_id(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "focus_start", {"task_id": "task1", "planned_minutes": 45}
                )
            ).content[0].text
        )
        assert payload["ok"] is True
        session = payload["session"]
        assert session["id"] == "s1" and session["status"] == "running"
        assert session["planned_minutes"] == 45

    async def test_pause_resume_finish_lifecycle(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        started = json.loads((await mcp.call_tool("focus_start", {})).content[0].text)
        sid = started["session"]["id"]

        paused = json.loads(
            (await mcp.call_tool("focus_pause", {"session_id": sid})).content[0].text
        )
        assert paused["session"]["status"] == "paused"

        resumed = json.loads(
            (await mcp.call_tool("focus_resume", {"session_id": sid})).content[0].text
        )
        assert resumed["session"]["status"] == "running"

        finished = json.loads(
            (await mcp.call_tool("focus_finish", {"session_id": sid})).content[0].text
        )
        assert finished["session"]["status"] == "finished"

    async def test_abandon(self, mcp_ctx):
        mcp, _ = mcp_ctx
        started = json.loads((await mcp.call_tool("focus_start", {})).content[0].text)
        sid = started["session"]["id"]
        payload = json.loads(
            (await mcp.call_tool("focus_abandon", {"session_id": sid})).content[0].text
        )
        assert payload["session"]["status"] == "abandoned"

    async def test_unknown_session_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("focus_pause", {"session_id": "s999"})
        assert "会话不存在" in str(ei.value)


class TestHabitWrite:
    async def test_checkin_defaults(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("habit_checkin", {"habit_id": "h1"})).content[0].text
        )
        assert payload["ok"] is True
        assert payload["result"] == {"ok": True, "date": "2026-11-09", "count": 1}
        req = [r for r in fake_backend.requests if r.url.path.endswith("/checkin")][-1]
        assert req.url.params["tz_offset_minutes"] == "480"

    async def test_checkin_validates_mood_and_amount(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("habit_checkin", {"habit_id": "h1", "mood": 9})
        assert "1-5" in str(ei.value)
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("habit_checkin", {"habit_id": "h1", "amount": 0})
        assert "1-999" in str(ei.value)

    async def test_checkin_with_all_fields(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "habit_checkin",
                    {
                        "habit_id": "h1",
                        "date": "2026-11-08",
                        "amount": 3,
                        "note": "跑了 5 公里",
                        "mood": 4,
                    },
                )
            ).content[0].text
        )
        assert payload["ok"] is True
        body = json.loads(
            [r for r in fake_backend.requests if r.url.path.endswith("/checkin")][-1].content
        )
        assert body["amount"] == 3 and body["mood"] == 4 and body["note"] == "跑了 5 公里"

    async def test_skip(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("habit_skip", {"habit_id": "h2"})).content[0].text
        )
        assert payload["ok"] is True and payload["result"]["skipped"] is True

    async def test_un_checkin(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "habit_un_checkin", {"habit_id": "h1", "date": "2026-11-08"}
                )
            ).content[0].text
        )
        assert payload["ok"] is True and payload["undone"] is True
        req = [r for r in fake_backend.requests if r.url.path.endswith("/checkin")][-1]
        assert req.method == "DELETE"
        assert req.url.params["date"] == "2026-11-08"
