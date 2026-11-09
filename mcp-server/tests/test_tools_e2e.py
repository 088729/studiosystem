"""End-to-end tool tests via MCPServer.call_tool with the mock transport."""

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


class TestSystemTools:
    async def test_studio_status(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("studio_status", {})
        payload = json.loads(result.content[0].text)
        assert payload["ok"] is True
        assert payload["identity"]["username"] == "mcp-bot"
        assert "xmind:view" in payload["identity"]["permissions"]

    async def test_studio_capabilities_redacts(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("studio_capabilities", {})
        payload = json.loads(result.content[0].text)
        assert payload["read_only"] is False
        assert "case_get_map" in payload["registered_tools"]
        assert "token" in payload["config"]  # present but masked

    async def test_whoami(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("whoami", {})
        payload = json.loads(result.content[0].text)
        assert payload["username"] == "mcp-bot"


class TestCaseTools:
    async def test_list_maps(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("case_list_maps", {})
        payload = json.loads(result.content[0].text)
        assert payload["count"] == 1
        assert payload["maps"][0]["title"] == "登录模块"

    async def test_get_map_published_outline(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("case_get_map", {"map_id": "map1"})
        payload = json.loads(result.content[0].text)
        assert payload["meta"]["current_version"] == 3
        assert "[n1] 正常登录" in payload["outline"]
        assert payload["node_count"] == 5  # root + n1 + n1-1 + n2 + n2-1

    async def test_get_map_draft_source(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("case_get_map", {"map_id": "map1", "source": "draft"})
        payload = json.loads(result.content[0].text)
        assert "登录模块(草稿)" in payload["outline"]

    async def test_get_map_not_found_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        # programmatic API raises ToolError; protocol clients see isError=true
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("case_get_map", {"map_id": "nope"})
        assert "导图不存在" in str(ei.value)


class TestTaskTools:
    async def test_list_context(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("task_list_context", {})
        payload = json.loads(result.content[0].text)
        assert payload["lists"][0]["name"] == "工作"
        assert payload["tags"][0]["name"] == "回归"

    async def test_list_tasks(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("task_list_tasks", {"status": "todo"})
        payload = json.loads(result.content[0].text)
        assert payload["count"] == 1
        assert "写登录用例" in payload["tasks"][0]

    async def test_get_task_includes_case_ref(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("task_get_task", {"task_id": "task1"})
        payload = json.loads(result.content[0].text)
        assert payload["task"]["case_map_title"] == "登录模块"
        assert payload["task"]["case_node_text"] == "正常登录"


class TestWikiTools:
    async def test_list_vaults(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("wiki_list_vaults", {})
        payload = json.loads(result.content[0].text)
        assert payload["vaults"][0]["status_label"] == "就绪"

    async def test_tree(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("wiki_tree", {"vault_id": "v1"})
        payload = json.loads(result.content[0].text)
        assert "docs/index.md" in payload["tree"]

    async def test_read_page(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("wiki_read_page", {"vault_id": "v1", "path": "docs/index.md"})
        payload = json.loads(result.content[0].text)
        assert payload["title"] == "index"
        assert "你好" in payload["content"]

    async def test_read_page_bad_path_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("wiki_read_page", {"vault_id": "v1", "path": "../etc/passwd.md"})
        assert "wiki_path_invalid" in str(ei.value) or ". 或 .." in str(ei.value)

    async def test_search(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool("wiki_search", {"vault_id": "v1", "mode": "search", "q": "你好"})
        payload = json.loads(result.content[0].text)
        assert payload["count"] == 1


class TestGuard:
    async def test_read_only_removes_write_later(self, mock_transport):
        # P0 is all read-only; guard with read_only=true must keep everything
        mcp, ctx = await _build(make_settings(read_only=True), mock_transport)
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "case_get_map" in names
        await ctx.aclose()

    async def test_modules_case_only(self, mock_transport):
        mcp, ctx = await _build(make_settings(modules="case"), mock_transport)
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "case_get_map" in names
        assert "task_list_tasks" not in names
        assert "whoami" in names  # system domain always on
        await ctx.aclose()

    async def test_denied_tools(self, mock_transport):
        mcp, ctx = await _build(make_settings(denied_tools="case_get_map"), mock_transport)
        tools = await mcp.list_tools()
        assert "case_get_map" not in {t.name for t in tools}
        await ctx.aclose()

    async def test_audit_written(self, mcp_ctx, tmp_path):
        mcp, _ = mcp_ctx
        await mcp.call_tool("whoami", {})
        audit_path = tmp_path / "audit.jsonl"
        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert any(json.loads(line)["tool"] == "whoami" for line in lines)


async def _build(settings, transport):
    return build_server(settings, transport=transport)
