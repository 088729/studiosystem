"""Protocol smoke: server/discover, tools/list determinism, stdio sanity."""

import pytest
from conftest import make_settings

from studiosystem_mcp.protocol.compat import gates_for
from studiosystem_mcp.protocol.discovery import build_identity, negotiate_version


class TestDiscovery:
    def test_identity_shape(self):
        ident = build_identity("0.1.0", ["2026-07-28", "2025-11-25"])
        d = ident.to_dict()
        assert d["supported_versions"] == ["2026-07-28", "2025-11-25"]
        assert d["capabilities"]["tools"] is True
        assert d["capabilities"]["prompts"] is True

    def test_negotiate_prefers_ours_in_order(self):
        supported = ("2026-07-28", "2025-11-25")
        assert negotiate_version(["2025-11-25", "2026-07-28"], supported) == "2026-07-28"
        assert negotiate_version(["2025-11-25"], supported) == "2025-11-25"
        assert negotiate_version(None, supported) == "2026-07-28"
        assert negotiate_version(["1999-01-01"], supported) == "2025-11-25"

    def test_gates(self):
        modern = gates_for("2026-07-28")
        legacy = gates_for("2025-11-25")
        assert modern.mrtr_input_required and not modern.elicitation
        assert legacy.elicitation and not legacy.mrtr_input_required
        assert modern.stateless_http and not legacy.stateless_http


class TestToolsList:
    async def test_deterministic_sorted(self, mock_transport):
        from studiosystem_mcp.server import build_server

        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            tools = await mcp.list_tools()
            names = [t.name for t in tools]
            assert names == sorted(names), "tools/list 必须确定性排序（§6.9 规范）"
            assert len(names) == 24  # 默认模块 case,task,wiki：3 系统 + 7 case + 7 task + 7 wiki
        finally:
            await ctx.aclose()


class TestStdioSanity:
    """stdio transport: server starts, answers one tools/list over real pipes."""

    async def test_stdio_smoke(self):
        pytest.importorskip("mcp")
        # A server wired to the mock transport can't span processes, so smoke-test
        # the stdio server with the real entry point against an unreachable backend:
        # tools/list must still work (it needs no backend I/O).
        import sys
        from pathlib import Path

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client


        project_root = Path(__file__).resolve().parent.parent
        server_params = StdioServerParameters(
            command=sys.executable,  # same interpreter → project venv with mcp deps
            args=["-m", "studiosystem_mcp", "--transport", "stdio"],
            cwd=str(project_root),
            env={
                "STUDIO_MCP_AUTH_MODE": "bearer",
                "STUDIO_MCP_TOKEN": "x",
                "STUDIO_MCP_STUDIO_BASE_URL": "http://127.0.0.1:9",  # unreachable
                "PYTHONPATH": str(project_root / "src"),
            },
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                names = sorted(t.name for t in result.tools)
                assert "studio_status" in names
                assert "case_get_map" in names
                # protocol version negotiation: initialize() exchanged version info
                assert session._initialize_result is not None
