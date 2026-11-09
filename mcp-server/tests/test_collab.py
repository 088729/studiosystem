"""P2 collab tests: comments / calendar / reminders / share members."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(audit_file=str(tmp_path / "audit.jsonl"), modules="task,collab"),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestTaskComment:
    async def test_list_empty_then_add(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        listed = json.loads(
            (await mcp.call_tool("task_comment", {"task_id": "task1"})).content[0].text
        )
        assert listed["ok"] is True and listed["count"] == 0

        added = json.loads(
            (
                await mcp.call_tool(
                    "task_comment", {"task_id": "task1", "action": "add", "content": "已复现"}
                )
            ).content[0].text
        )
        assert added["ok"] is True and added["comment"]["content"] == "已复现"

        listed = json.loads(
            (await mcp.call_tool("task_comment", {"task_id": "task1"})).content[0].text
        )
        assert listed["count"] == 1

    async def test_add_requires_content(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("task_comment", {"task_id": "task1", "action": "add"})
        assert "content" in str(ei.value)

    async def test_unknown_action(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("task_comment", {"task_id": "task1", "action": "delete"})
        assert "未知 action" in str(ei.value)


class TestCalendarRange:
    async def test_range_query(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "calendar_range",
                    {"start": "2026-11-01T00:00:00", "end": "2026-11-30T00:00:00"},
                )
            ).content[0].text
        )
        assert payload["ok"] is True and payload["count"] == 1
        assert "写登录用例" in payload["tasks"][0]  # format_task_line 文本行


class TestReminders:
    async def test_pending_and_ack(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        pending = json.loads(
            (await mcp.call_tool("pending_reminders", {})).content[0].text
        )
        assert pending["ok"] is True and pending["count"] == 1
        assert pending["reminders"][0]["task_id"] == "task1"

        ack = json.loads(
            (await mcp.call_tool("reminder_ack", {"task_id": "task1"})).content[0].text
        )
        assert ack["ok"] is True and ack["snoozed"] is False

        ack = json.loads(
            (
                await mcp.call_tool(
                    "reminder_ack", {"task_id": "task1", "snooze_minutes": 30}
                )
            ).content[0].text
        )
        assert ack["snoozed"] is True
        ack_reqs = [
            r for r in fake_backend.requests if r.url.path.endswith("/reminders/ack")
        ]
        assert json.loads(ack_reqs[-1].content) == {"snooze_minutes": 30}


class TestShareMembers:
    async def test_list_and_add(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        listed = json.loads(
            (await mcp.call_tool("share_members", {"list_id": "l1"})).content[0].text
        )
        assert listed["count"] == 1

        added = json.loads(
            (
                await mcp.call_tool(
                    "share_members",
                    {"list_id": "l1", "action": "add", "username": "alice", "role": "editor"},
                )
            ).content[0].text
        )
        assert added["ok"] is True
        assert {"username": "alice", "role": "editor"} in added["members"]

    async def test_invalid_role(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "share_members",
                {"list_id": "l1", "action": "add", "username": "alice", "role": "admin"},
            )
        assert "viewer 或 editor" in str(ei.value)
