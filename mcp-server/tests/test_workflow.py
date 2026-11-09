"""P2 workflow tests: wiki generation from tasks/case, outline → tasks."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server

WORKFLOW_MODULES = "case,task,wiki,analytics,focus,habits,git,collab,workflow"


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(
            audit_file=str(tmp_path / "audit.jsonl"),
            modules=WORKFLOW_MODULES,
            default_vault_id="v1",
        ),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


async def _confirm_and_run(mcp, tool, args):
    """First call gets the token, second call (same args + token) executes."""
    first = json.loads((await mcp.call_tool(tool, args)).content[0].text)
    assert first["requires_confirmation"] is True, first
    return json.loads(
        (await mcp.call_tool(tool, {**args, "confirm_token": first["confirm_token"]})).content[0].text
    )


class TestGenerateWikiFromTasks:
    async def test_generates_renders_and_commits(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "generate_wiki_from_tasks",
            {"range": "week", "path": "reports/weekly.md", "message": "docs: 周报 2026-11-09 by MCP"},
        )
        assert result["ok"] is True and result["committed"] is True
        page = fake_backend.pages["reports/weekly.md"]
        assert "任务周报" in page
        assert "## 待办（2）" in page  # 来自 summary/preview 的 groups 渲染
        assert "写登录用例" in page  # 明细底稿
        # summary/preview 请求带上了 range 与时区
        preview_reqs = [r for r in fake_backend.requests if r.url.path == "/api/v1/task/summary/preview"]
        body = json.loads(preview_reqs[0].content)
        assert body["range"] == "week" and body["tz_offset_minutes"] == 480

    async def test_content_override_skips_render(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "generate_wiki_from_tasks",
            {"range": "week", "path": "reports/manual.md", "content": "# 手工润色稿"},
        )
        assert result["ok"] is True
        assert fake_backend.pages["reports/manual.md"] == "# 手工润色稿"

    async def test_default_path_uses_date_placeholder(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "generate_wiki_from_tasks",
            {"range": "week", "message": "docs: 周报"},
        )
        assert result["ok"] is True
        # default_wiki_path = reports/{date}.md
        assert any(p.startswith("reports/2026-") and p.endswith(".md") for p in fake_backend.pages)

    async def test_missing_vault_is_error(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(modules=WORKFLOW_MODULES, default_vault_id=None),
            transport=mock_transport,
        )
        try:
            with pytest.raises(Exception) as ei:
                await mcp.call_tool("generate_wiki_from_tasks", {"range": "week"})
            assert "DEFAULT_VAULT_ID" in str(ei.value)
        finally:
            await ctx.aclose()

    async def test_existing_page_requires_overwrite(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        fake_backend.pages["reports/exists.md"] = "# 旧"
        first = json.loads(
            (
                await mcp.call_tool(
                    "generate_wiki_from_tasks",
                    {"range": "week", "path": "reports/exists.md", "content": "# 新"},
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        assert first["preview"]["exists"] is True
        assert "-# 旧" in first["preview"]["diff"]


class TestGenerateWikiFromCase:
    async def test_renders_case_outline(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "generate_wiki_from_case",
            {"map_id": "map1", "path": "specs/login.md"},
        )
        assert result["ok"] is True
        page = fake_backend.pages["specs/login.md"]
        assert "登录模块 用例规格" in page
        assert "source_case_map: \"map1\"" in page
        assert "[[登录模块]]" in page  # 来源双链
        assert "输入正确账号密码" in page and "`n1-1`" in page

    async def test_unknown_map_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "generate_wiki_from_case", {"map_id": "nope", "path": "specs/x.md"}
            )
        assert "不存在" in str(ei.value) or "没有" in str(ei.value)


class TestCaseOutlineToTasks:
    async def test_creates_tasks_for_leaves_with_backfill(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp, "case_outline_to_tasks", {"map_id": "map1", "list_id": "l1"}
        )
        assert result["ok"] is True
        # map1 有 2 个叶子：输入正确账号密码 / 密码错误
        assert result["created_count"] == 2 and result["failed_count"] == 0
        creates = [
            json.loads(r.content)
            for r in fake_backend.requests
            if r.url.path == "/api/v1/task/tasks" and r.method == "POST"
        ]
        assert {c["title"] for c in creates} == {"输入正确账号密码", "密码错误"}
        for c in creates:
            assert c["case_map_id"] == "map1"
            assert c["case_node_id"] in ("n1-1", "n2-1")
            assert c["list_id"] == "l1"

    async def test_parent_uid_scopes_subtree(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp, "case_outline_to_tasks", {"map_id": "map1", "parent_uid": "n1"}
        )
        assert result["created_count"] == 1
        titles = [c["title"] for c in result["created"]]
        assert titles == ["输入正确账号密码"]

    async def test_unknown_parent_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "case_outline_to_tasks", {"map_id": "map1", "parent_uid": "nope"}
            )
        assert "找不到节点" in str(ei.value)

    async def test_dry_run_previews_without_creating(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        before = len([r for r in fake_backend.requests if r.url.path == "/api/v1/task/tasks" and r.method == "POST"])
        payload = json.loads(
            (
                await mcp.call_tool(
                    "case_outline_to_tasks",
                    {"map_id": "map1", "dry_run": True},
                )
            ).content[0].text
        )
        assert payload["dry_run"] is True
        assert payload["preview"]["leaf_count"] == 2
        after = len([r for r in fake_backend.requests if r.url.path == "/api/v1/task/tasks" and r.method == "POST"])
        assert after == before
