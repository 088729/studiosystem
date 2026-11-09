"""P3 rate-limit tests: token bucket unit behavior + MCP boundary enforcement."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.policy.ratelimit import TokenBucketLimiter
from studiosystem_mcp.server import build_server


class TestBucketUnit:
    def test_burst_then_throttle(self):
        clock = [0.0]
        limiter = TokenBucketLimiter(2, clock=lambda: clock[0])
        assert limiter.acquire() and limiter.acquire()  # 2 个令牌（整个窗口）
        assert not limiter.acquire()  # 桶空
        clock[0] += 30  # 30s 回 1 个
        assert limiter.acquire()
        assert not limiter.acquire()

    def test_disabled_when_zero(self):
        limiter = TokenBucketLimiter(0)
        assert all(limiter.acquire() for _ in range(1000))

    def test_per_key_isolation(self):
        limiter = TokenBucketLimiter(1)
        assert limiter.acquire("a")
        assert not limiter.acquire("a")
        assert limiter.acquire("b")  # 不同身份互不影响

    def test_retry_after_estimate(self):
        clock = [0.0]
        limiter = TokenBucketLimiter(60, clock=lambda: clock[0])  # 1 token/s
        for _ in range(60):  # 掏空桶
            assert limiter.acquire()
        assert limiter.retry_after_seconds() == pytest.approx(1.0, abs=0.05)


class TestMcpBoundary:
    async def test_throttled_call_is_error(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(rate_limit_per_minute=2), transport=mock_transport
        )
        try:
            ok1 = json.loads((await mcp.call_tool("whoami", {})).content[0].text)
            ok2 = json.loads((await mcp.call_tool("whoami", {})).content[0].text)
            assert ok1["ok"] and ok2["ok"]
            with pytest.raises(Exception) as ei:
                await mcp.call_tool("whoami", {})
            assert "限流" in str(ei.value)
        finally:
            await ctx.aclose()

    async def test_disabled_by_default_settings(self, mock_transport):
        # 默认 30/min：连打 5 次不应触发（部署默认值回归保护）
        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            for _ in range(5):
                payload = json.loads((await mcp.call_tool("whoami", {})).content[0].text)
                assert payload["ok"] is True
        finally:
            await ctx.aclose()
