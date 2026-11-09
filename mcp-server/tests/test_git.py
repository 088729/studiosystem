"""P2 git-domain tests: vault status / history / revert / pull / push / commit / reindex."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server

GIT_MODULES = "wiki,git"


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(
            audit_file=str(tmp_path / "audit.jsonl"),
            modules=GIT_MODULES,
            default_vault_id="v1",
        ),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestVaultStatus:
    async def test_detail_with_changes(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("vault_status", {})).content[0].text)
        assert payload["ok"] is True
        assert payload["vault_id"] == "v1"
        assert payload["changes"] == ["docs/index.md"]
        assert payload["doc_count"] == 1

    async def test_explicit_vault_id(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("vault_status", {"vault_id": "v1"})).content[0].text
        )
        assert payload["ok"] is True

    async def test_missing_vault_and_no_default_is_error(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(modules=GIT_MODULES, default_vault_id=None),
            transport=mock_transport,
        )
        try:
            with pytest.raises(Exception) as ei:
                await mcp.call_tool("vault_status", {})
            assert "DEFAULT_VAULT_ID" in str(ei.value)
        finally:
            await ctx.aclose()


class TestPageHistoryAndDiff:
    async def test_history_list(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "page_history", {"vault_id": "v1", "path": "docs/index.md"}
                )
            ).content[0].text
        )
        assert payload["ok"] is True and payload["count"] == 2
        assert payload["entries"][0]["commit"] == "abc1234"

    async def test_diff(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "page_diff",
                    {"vault_id": "v1", "path": "docs/index.md", "commit": "abc1234"},
                )
            ).content[0].text
        )
        assert payload["ok"] is True and "+新" in payload["diff"]


class TestPageRevert:
    async def test_requires_allow_destructive(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "page_revert",
                {"vault_id": "v1", "path": "docs/index.md", "commit": "def5678"},
            )
        assert "ALLOW_DESTRUCTIVE" in str(ei.value)

    async def test_revert_with_flag_and_confirm(self, mcp_ctx, fake_backend):
        mcp, ctx = mcp_ctx
        ctx.settings.allow_destructive = True
        first = json.loads(
            (
                await mcp.call_tool(
                    "page_revert",
                    {"vault_id": "v1", "path": "docs/index.md", "commit": "def5678"},
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        second = json.loads(
            (
                await mcp.call_tool(
                    "page_revert",
                    {
                        "vault_id": "v1",
                        "path": "docs/index.md",
                        "commit": "def5678",
                        "confirm_token": first["confirm_token"],
                    },
                )
            ).content[0].text
        )
        assert second["ok"] is True
        assert fake_backend.pages["docs/index.md"] == "# 回滚到 def5678"


class TestPullPushCommit:
    async def test_pull_requires_confirm(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads((await mcp.call_tool("vault_pull", {})).content[0].text)
        assert first["requires_confirmation"] is True
        assert first["preview"]["action"] == "pull"
        second = json.loads(
            (
                await mcp.call_tool(
                    "vault_pull", {"confirm_token": first["confirm_token"]}
                )
            ).content[0].text
        )
        assert second["ok"] is True and second["result"]["message"] == "pull 完成"

    async def test_push_requires_allow_destructive(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("vault_push", {})
        assert "ALLOW_DESTRUCTIVE" in str(ei.value)

    async def test_push_with_flag(self, mcp_ctx, fake_backend):
        mcp, ctx = mcp_ctx
        ctx.settings.allow_destructive = True
        first = json.loads((await mcp.call_tool("vault_push", {})).content[0].text)
        assert first["requires_confirmation"] is True
        second = json.loads(
            (
                await mcp.call_tool(
                    "vault_push", {"confirm_token": first["confirm_token"]}
                )
            ).content[0].text
        )
        assert second["ok"] is True and second["result"]["message"] == "push 完成"

    async def test_commit_with_message(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (
                await mcp.call_tool(
                    "vault_commit", {"message": "docs: 手动提交", "vault_id": "v1"}
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        second = json.loads(
            (
                await mcp.call_tool(
                    "vault_commit",
                    {
                        "message": "docs: 手动提交",
                        "vault_id": "v1",
                        "confirm_token": first["confirm_token"],
                    },
                )
            ).content[0].text
        )
        assert second["ok"] is True
        assert second["commit"]["message"] == "docs: 手动提交"


class TestWikiReindex:
    async def test_start_and_conflict(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads((await mcp.call_tool("wiki_reindex", {})).content[0].text)
        assert first["ok"] is True and first["status"] == "running"
        # 重建中再次触发 → 409 归一化为可读错误
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("wiki_reindex", {})
        assert "重建中" in str(ei.value)
