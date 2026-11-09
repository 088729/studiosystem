"""P1 task write tests: quick-add create, idempotency, update semantics, delete tiers, batch."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(audit_file=str(tmp_path / "audit.jsonl")),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestTaskCreate:
    async def test_quick_add_full(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_create", {"text": "写登录用例 @明天 !高 ~回归 #工作"})).content[0].text
        )
        assert payload["ok"] is True
        assert payload["list_resolution"] == "工作 → l1"
        task = payload["task_raw"]
        assert task["title"] == "写登录用例"
        assert task["priority"] == 3
        assert task["tags"] == ["回归"]
        assert task["due_at"] is not None and task["due_at"] > "2026-11-09"  # @明天
        assert task["list_id"] == "l1"

    async def test_quick_add_unmatched_list_falls_to_inbox(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_create", {"text": "买牛奶 #不存在的清单"})).content[0].text
        )
        assert payload["ok"] is True
        assert payload["task_raw"]["list_id"] is None
        assert "未命中" in payload["list_resolution"]

    async def test_structured_fields_override_quickadd(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool(
                "task_create", {"text": "复习 @明天 !高", "priority": 1, "due_at": "2026-12-01", "tags": ["学习"]}
            )).content[0].text
        )
        task = payload["task_raw"]
        assert task["priority"] == 1
        assert task["due_at"] == "2026-12-01"
        assert task["tags"] == ["学习"]

    async def test_idempotency_key_replay(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        args = {"title": "幂等任务", "idempotency_key": "key-1"}
        first = json.loads((await mcp.call_tool("task_create", args)).content[0].text)
        assert first["ok"] is True and "idempotent_replay" not in first
        second = json.loads((await mcp.call_tool("task_create", args)).content[0].text)
        assert second["idempotent_replay"] is True
        assert second["task_raw"]["id"] == first["task_raw"]["id"]
        creates = [r for r in fake_backend.requests if r.url.path == "/api/v1/task/tasks" and r.method == "POST"]
        assert len(creates) == 1

    async def test_dry_run(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_create", {"text": "看看就好", "dry_run": True})).content[0].text
        )
        assert payload["dry_run"] is True
        assert payload["preview"]["payload"]["title"] == "看看就好"

    async def test_bad_quick_add_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("task_create", {"text": "@NotADate 标题"})
        assert "无法识别日期" in str(ei.value)


class TestTaskUpdate:
    async def test_patch_fields(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_update", {"task_id": "task1", "priority": 1, "due_at": "2026-11-20"})).content[0].text
        )
        assert payload["ok"] is True

    async def test_clear_due(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("task_update", {"task_id": "task1", "clear_due": True})).content[0].text
        )
        assert payload["ok"] is True

    async def test_complete_and_uncomplete(self, mcp_ctx):
        mcp, _ = mcp_ctx
        done = json.loads((await mcp.call_tool("task_update", {"task_id": "task1", "action": "complete"})).content[0].text)
        assert "已完成" in done["task"]
        undone = json.loads((await mcp.call_tool("task_update", {"task_id": "task1", "action": "uncomplete"})).content[0].text)
        assert "已完成" not in undone["task"]

    async def test_skip(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("task_update", {"task_id": "task1", "action": "skip"})).content[0].text)
        assert "已跳过" in payload["task"]

    async def test_no_fields_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("task_update", {"task_id": "task1"})
        assert "没有可更新的字段" in str(ei.value)


class TestTaskDelete:
    async def test_soft_delete_one_step(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("task_delete", {"task_id": "task1"})).content[0].text)
        assert payload["ok"] is True and payload["recoverable"] is True

    async def test_restore(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("task_delete", {"task_id": "task1", "mode": "restore"})).content[0].text)
        assert payload["ok"] is True

    async def test_purge_requires_allow_destructive(self, mock_transport):
        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            tools = {t.name for t in await mcp.list_tools()}
            assert "task_delete" in tools  # 工具注册；purge 子操作受 allow_destructive 控制
            with pytest.raises(Exception) as ei:
                await mcp.call_tool("task_delete", {"task_id": "task1", "mode": "purge"})
            assert "ALLOW_DESTRUCTIVE" in str(ei.value)
        finally:
            await ctx.aclose()

        mcp2, ctx2 = build_server(make_settings(allow_destructive=True), transport=mock_transport)
        try:
            first = json.loads(
                (await mcp2.call_tool("task_delete", {"task_id": "task1", "mode": "purge"})).content[0].text
            )
            assert first["requires_confirmation"] is True
            second = json.loads(
                (await mcp2.call_tool(
                    "task_delete", {"task_id": "task1", "mode": "purge", "confirm_token": first["confirm_token"]}
                )).content[0].text
            )
            assert second["ok"] is True and second["mode"] == "purge"
        finally:
            await ctx2.aclose()


class TestTaskBatch:
    async def test_batch_forces_confirmation(self, mcp_ctx):
        mcp, _ = mcp_ctx
        first = json.loads(
            (await mcp.call_tool("task_batch", {"ids": ["task1", "task2"], "action": "complete"})).content[0].text
        )
        assert first["requires_confirmation"] is True
        assert first["preview"]["affected"] == 2
        second = json.loads(
            (await mcp.call_tool(
                "task_batch",
                {"ids": ["task1", "task2"], "action": "complete", "confirm_token": first["confirm_token"]},
            )).content[0].text
        )
        assert second["ok"] is True

    async def test_empty_ids_rejected(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("task_batch", {"ids": [], "action": "complete"})
        assert "ids 不能为空" in str(ei.value)
