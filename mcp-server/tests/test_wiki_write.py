"""P2 wiki write tests: create / overwrite-with-confirm flow / history & revert."""

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


def _calls(fake_backend, path, method=None):
    return [
        r
        for r in fake_backend.requests
        if r.url.path == path and (method is None or r.method == method)
    ]


class TestWikiCreatePage:
    async def test_create_new_page(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "wiki_create_page", {"vault_id": "v1", "path": "docs/new.md", "content": "# 新页"}
                )
            ).content[0].text
        )
        assert payload["ok"] is True and payload["created"] is True
        assert fake_backend.pages["docs/new.md"] == "# 新页"

    async def test_existing_page_is_error(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "wiki_create_page", {"vault_id": "v1", "path": "docs/index.md", "content": "# 覆盖"}
            )
        assert "已存在" in str(ei.value)

    async def test_invalid_path_rejected_before_any_request(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        before = len(fake_backend.requests)
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "wiki_create_page", {"vault_id": "v1", "path": "../escape.md", "content": "x"}
            )
        assert "wiki_path_invalid" in str(ei.value)
        assert len(fake_backend.requests) == before  # 本地预校验，未发请求

    async def test_dry_run(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (
                await mcp.call_tool(
                    "wiki_create_page",
                    {"vault_id": "v1", "path": "docs/x.md", "content": "# x", "dry_run": True},
                )
            ).content[0].text
        )
        assert payload["dry_run"] is True
        assert "docs/x.md" not in fake_backend.pages


class TestWikiWritePage:
    async def test_new_page_requires_confirmation_then_writes(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (
                await mcp.call_tool(
                    "wiki_write_page",
                    {"vault_id": "v1", "path": "reports/a.md", "content": "# 报告", "message": "docs: a"},
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        assert first["preview"]["exists"] is False

        second = json.loads(
            (
                await mcp.call_tool(
                    "wiki_write_page",
                    {
                        "vault_id": "v1",
                        "path": "reports/a.md",
                        "content": "# 报告",
                        "message": "docs: a",
                        "confirm_token": first["confirm_token"],
                    },
                )
            ).content[0].text
        )
        assert second["ok"] is True and second["committed"] is True
        assert second["commit"]["message"] == "docs: a"
        assert fake_backend.pages["reports/a.md"] == "# 报告"
        # lock → PUT → commit → release 顺序（取最后一次写入序列，忽略前置 GET）
        seq = [
            (r.method, r.url.path)
            for r in fake_backend.requests
            if r.url.path.startswith("/api/v1/wiki/vaults/v1/pages") and r.method != "GET"
        ][-4:]
        assert seq == [
            ("POST", "/api/v1/wiki/vaults/v1/pages/lock"),
            ("PUT", "/api/v1/wiki/vaults/v1/pages/content"),
            ("POST", "/api/v1/wiki/vaults/v1/pages/commit"),
            ("DELETE", "/api/v1/wiki/vaults/v1/pages/lock"),
        ]
        assert fake_backend.page_locks == {}  # 锁已释放

    async def test_existing_page_shows_diff_and_refuses_overwrite(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (
                await mcp.call_tool(
                    "wiki_write_page",
                    {"vault_id": "v1", "path": "docs/index.md", "content": "# 新首页"},
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        assert first["preview"]["exists"] is True
        assert "-你好" in (first["preview"]["diff"] or "")  # unified diff 含旧内容

        # 用同一 token + overwrite=false 执行 → 拒绝且不发送写请求
        writes_before = len(_calls(fake_backend, "/api/v1/wiki/vaults/v1/pages/content", "PUT"))
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "wiki_write_page",
                {
                    "vault_id": "v1",
                    "path": "docs/index.md",
                    "content": "# 新首页",
                    "confirm_token": first["confirm_token"],
                },
            )
        assert "overwrite=false" in str(ei.value)
        assert len(_calls(fake_backend, "/api/v1/wiki/vaults/v1/pages/content", "PUT")) == writes_before
        assert fake_backend.pages["docs/index.md"] == "# 首页\n\n你好"

    async def test_overwrite_true_full_flow(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        args = {"vault_id": "v1", "path": "docs/index.md", "content": "# 新首页", "overwrite": True}
        first = json.loads((await mcp.call_tool("wiki_write_page", args)).content[0].text)
        assert first["requires_confirmation"] is True
        second = json.loads(
            (
                await mcp.call_tool(
                    "wiki_write_page", {**args, "confirm_token": first["confirm_token"]}
                )
            ).content[0].text
        )
        assert second["ok"] is True and second["overwritten"] is True
        assert fake_backend.pages["docs/index.md"] == "# 新首页"

    async def test_confirm_mode_none_executes_directly(self, mock_transport, fake_backend):
        mcp, ctx = build_server(
            make_settings(confirm_mode="none"), transport=mock_transport
        )
        try:
            payload = json.loads(
                (
                    await mcp.call_tool(
                        "wiki_write_page", {"vault_id": "v1", "path": "reports/none.md", "content": "# n"}
                    )
                ).content[0].text
            )
            assert payload["ok"] is True
            assert fake_backend.pages["reports/none.md"] == "# n"
        finally:
            await ctx.aclose()

    async def test_lock_released_when_put_fails(self, mock_transport, fake_backend):
        mcp, ctx = build_server(
            make_settings(confirm_mode="none"), transport=mock_transport
        )
        fake_backend.put_conflict = True
        try:
            with pytest.raises(Exception) as ei:
                await mcp.call_tool(
                    "wiki_write_page",
                    {"vault_id": "v1", "path": "reports/fail.md", "content": "# f"},
                )
            assert "锁定" in str(ei.value) or "423" in str(ei.value)
            # release 兜底：即便 PUT 失败也发了 release
            releases = _calls(fake_backend, "/api/v1/wiki/vaults/v1/pages/lock", "DELETE")
            assert len(releases) == 1
        finally:
            await ctx.aclose()


class TestWikiHistory:
    async def test_list_and_diff(self, mcp_ctx):
        mcp, _ = mcp_ctx
        listed = json.loads(
            (
                await mcp.call_tool(
                    "wiki_history", {"vault_id": "v1", "path": "docs/index.md", "action": "list"}
                )
            ).content[0].text
        )
        assert listed["ok"] is True and listed["count"] == 2

        diffed = json.loads(
            (
                await mcp.call_tool(
                    "wiki_history",
                    {"vault_id": "v1", "path": "docs/index.md", "action": "diff", "commit": "abc1234"},
                )
            ).content[0].text
        )
        assert diffed["diff"] and diffed["truncated"] is False

    async def test_revert_requires_allow_destructive(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "wiki_history",
                {"vault_id": "v1", "path": "docs/index.md", "action": "revert", "commit": "def5678"},
            )
        assert "ALLOW_DESTRUCTIVE" in str(ei.value)

    async def test_revert_with_flag_and_confirm(self, mcp_ctx, fake_backend):
        mcp, ctx = mcp_ctx
        ctx.settings.allow_destructive = True  # noqa: SLF001 - 测试内联切换
        first = json.loads(
            (
                await mcp.call_tool(
                    "wiki_history",
                    {"vault_id": "v1", "path": "docs/index.md", "action": "revert", "commit": "def5678"},
                )
            ).content[0].text
        )
        assert first["requires_confirmation"] is True
        second = json.loads(
            (
                await mcp.call_tool(
                    "wiki_history",
                    {
                        "vault_id": "v1",
                        "path": "docs/index.md",
                        "action": "revert",
                        "commit": "def5678",
                        "confirm_token": first["confirm_token"],
                    },
                )
            ).content[0].text
        )
        assert second["ok"] is True
        assert fake_backend.pages["docs/index.md"] == "# 回滚到 def5678"
