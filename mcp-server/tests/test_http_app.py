"""HTTP transport smoke: outer bearer auth middleware behavior."""

import httpx
from conftest import make_settings

from studiosystem_mcp.__main__ import _wrap_with_auth
from studiosystem_mcp.server import build_server


async def _echo_app(scope, receive, send):
    """Minimal ASGI app: 200 + scope type. Stands in for the MCP HTTP app."""
    assert scope["type"] == "http"
    body = b'{"ok":true}'
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


class TestOuterAuth:
    async def test_rejects_missing_token(self):
        app = _wrap_with_auth(_echo_app, make_settings(mcp_token="outer-secret"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/mcp", json={})
            assert resp.status_code == 401

    async def test_rejects_wrong_token(self):
        app = _wrap_with_auth(_echo_app, make_settings(mcp_token="outer-secret"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/mcp", json={}, headers={"Authorization": "Bearer nope"})
            assert resp.status_code == 401

    async def test_accepts_correct_token(self):
        app = _wrap_with_auth(_echo_app, make_settings(mcp_token="outer-secret"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/mcp", json={}, headers={"Authorization": "Bearer outer-secret"})
            assert resp.status_code == 200

    async def test_no_token_configured_allows_all(self):
        app = _wrap_with_auth(_echo_app, make_settings(mcp_token=None))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/mcp", json={})
            assert resp.status_code == 200


class TestHttpAppBuilds:
    async def test_streamable_http_app_created(self, mock_transport):
        mcp, ctx = build_server(make_settings(transport="http"), transport=mock_transport)
        try:
            app = mcp.streamable_http_app(stateless_http=True, json_response=True)
            assert app is not None
        finally:
            await ctx.aclose()
