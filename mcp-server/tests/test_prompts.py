"""P2 prompts tests: list + get prompt content."""

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


class TestPrompts:
    async def test_all_prompts_listed(self, mcp_ctx):
        mcp, _ = mcp_ctx
        prompts = await mcp.list_prompts()
        names = {p.name for p in prompts}
        assert names == {"weekly_report", "testcase_spec", "retro", "case_review", "standup"}

    async def test_prompt_content_has_safety_rules(self, mcp_ctx):
        mcp, _ = mcp_ctx
        for name in ("weekly_report", "case_review"):
            result = await mcp.get_prompt(name, {})
            text = result.messages[0].content.text
            assert "confirm_token" in text  # 内置安全约束
            assert "dry_run" in text

    async def test_standup_is_readonly(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.get_prompt("standup", {})
        text = result.messages[0].content.text
        assert "纯只读" in text
