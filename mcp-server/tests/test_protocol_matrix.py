"""Protocol compatibility matrix (P3, §8.3): both supported protocol versions
(2026-07-28 modern, 2025-11-25 legacy) must answer tools/list, a read-only
call, and the token confirmation flow identically — the degradation contract.

If a future feature gates itself behind `gates_for(version)`, these tests pin
the legacy behavior so a modern-only regression is caught in CI.
"""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.protocol.compat import gates_for
from studiosystem_mcp.protocol.discovery import negotiate_version
from studiosystem_mcp.server import build_server

VERSIONS = ["2026-07-28", "2025-11-25"]


def _negotiated(client_versions: list[str]) -> str:
    return negotiate_version(client_versions, tuple(VERSIONS))


@pytest.mark.parametrize("version", VERSIONS)
class TestProtocolMatrix:
    async def test_negotiation_selects_version(self, version):
        assert _negotiated([version]) == version
        gates = gates_for(_negotiated([version]))
        assert gates.version == version
        if version == "2026-07-28":
            assert gates.mrtr_input_required and not gates.elicitation
        else:
            assert gates.elicitation and not gates.mrtr_input_required

    async def test_tools_list_identical(self, mock_transport, version):
        mcp, ctx = build_server(
            make_settings(protocol_versions=",".join(VERSIONS)),
            transport=mock_transport,
        )
        try:
            tools = await mcp.list_tools()
            names = [t.name for t in tools]
            assert names == sorted(names) and len(names) == 24
            # identity 声明支持的两个版本都包含协商结果
            assert version in ctx.protocol_identity["supported_versions"]
        finally:
            await ctx.aclose()

    async def test_readonly_call_works(self, mock_transport, version):
        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            payload = json.loads((await mcp.call_tool("studio_status", {})).content[0].text)
            assert payload["ok"] is True
        finally:
            await ctx.aclose()

    async def test_confirm_flow_degrades_identically(self, mock_transport, version, fake_backend):
        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            # 两阶段确认（token 通道）在两个协议版本下行为必须一致：
            # 第一发返回预览 + 令牌，第二发带令牌执行 lock→PUT→commit→release。
            args = {"vault_id": "v1", "path": f"reports/{version}.md", "content": "# x"}
            first = json.loads((await mcp.call_tool("wiki_write_page", args)).content[0].text)
            assert first["requires_confirmation"] is True
            second = json.loads(
                (
                    await mcp.call_tool(
                        "wiki_write_page", {**args, "confirm_token": first["confirm_token"]}
                    )
                ).content[0].text
            )
            assert second["ok"] is True and second["committed"] is True
            assert fake_backend.pages[f"reports/{version}.md"] == "# x"
        finally:
            await ctx.aclose()


class TestVersionFallback:
    def test_unknown_client_version_falls_back_to_legacy_baseline(self):
        assert _negotiated(["1999-01-01"]) == "2025-11-25"

    def test_no_client_version_prefers_ours(self):
        assert _negotiated(None) == "2026-07-28"
