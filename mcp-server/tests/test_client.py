"""HTTP client tests: auth modes, 401 re-login retry, error normalization."""

import httpx
import pytest
from conftest import make_settings

from studiosystem_mcp.client.http import StudioClient
from studiosystem_mcp.errors import StudioError


class TestPasswordAuth:
    async def test_login_and_cache(self, mock_transport, fake_backend):
        s = make_settings(auth_mode="password", username="mcp-bot", password="pw", token=None)
        client = StudioClient(s, transport=mock_transport)
        me = await client.get("/common/auth/me")
        assert me["username"] == "mcp-bot"
        # login happened once (first call), second call reused the token
        login_calls = [r for r in fake_backend.requests if r.url.path.endswith("/auth/login")]
        assert len(login_calls) == 1

    async def test_401_triggers_relogin_once(self, mock_transport, fake_backend):
        s = make_settings(auth_mode="password", username="mcp-bot", password="pw", token=None)
        client = StudioClient(s, transport=mock_transport)
        await client.get("/common/auth/me")  # login

        # expire the token: backend now rejects it, but accepts after re-login
        calls = {"n": 0}
        orig = fake_backend.handler

        def flaky(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/auth/login"):
                return orig(request)
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(401, json={"detail": {"code": "unauthorized", "message": "过期"}})
            return orig(request)

        client._client._transport = httpx.MockTransport(flaky)
        me = await client.get("/common/auth/me")
        assert me["username"] == "mcp-bot"

    async def test_persistent_401_raises(self, mock_transport, fake_backend):
        s = make_settings(auth_mode="bearer", token="bad-token")
        client = StudioClient(s, transport=mock_transport)
        with pytest.raises(StudioError) as ei:
            await client.get("/common/auth/me")
        assert ei.value.status == 401


class TestErrors:
    async def test_backend_error_normalized(self, mock_transport):
        s = make_settings()
        client = StudioClient(s, transport=mock_transport)
        with pytest.raises(StudioError) as ei:
            await client.get("/case/maps/does-not-exist")
        err = ei.value
        assert err.code == "map_not_found"
        assert err.status == 404
        assert "导图不存在" in err.message

    async def test_403_hint(self, mock_transport, fake_backend):
        def no_perms(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/health":
                return httpx.Response(200, json={})
            return httpx.Response(403, json={"detail": {"code": "forbidden", "message": "无权限"}})

        client = StudioClient(make_settings(), transport=httpx.MockTransport(no_perms))
        with pytest.raises(StudioError) as ei:
            await client.get("/task/lists")
        assert "extra_permissions" in (ei.value.hint or "")

    async def test_get_retry_on_5xx(self, fake_backend):
        state = {"n": 0}

        def flaky(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/health":
                return httpx.Response(200, json={})
            if request.url.path.endswith("/auth/me"):
                state["n"] += 1
                if state["n"] == 1:
                    return httpx.Response(502, json={"detail": "bad gateway"})
                return httpx.Response(200, json={"username": "u", "role_name": "viewer", "perms": []})
            return httpx.Response(404, json={"detail": {"code": "nf", "message": "x"}})

        s = make_settings(retry=2)
        client = StudioClient(s, transport=httpx.MockTransport(flaky))
        me = await client.get("/common/auth/me")
        assert me["username"] == "u"
        assert state["n"] == 2


class TestIdempotency:
    def test_memory_store(self):
        from studiosystem_mcp.client.idempotency import MemoryIdempotencyStore

        store = MemoryIdempotencyStore()
        assert store.get("k") is None
        store.put("k", {"v": 1}, ttl_seconds=60)
        assert store.get("k") == {"v": 1}
