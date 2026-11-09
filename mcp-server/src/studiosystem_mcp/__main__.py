"""CLI entry: `studiosystem-mcp [--transport stdio|http] [--config path]`.

Dual transport from P0 (decision Q2):
- stdio: default; logs go to stderr only (stdout is the protocol channel).
- http: Streamable HTTP (stateless) on host:port, with an outer shared-secret
  bearer check when STUDIO_MCP_MCP_TOKEN is set. Without the token the server
  refuses to bind to non-loopback addresses unless the operator explicitly
  opts in via STUDIO_MCP_INSECURE_DEV_ONLY=true.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .server import build_server
from .settings import get_settings


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studiosystem-mcp", description="Studio System MCP server")
    p.add_argument("--transport", choices=["stdio", "http"], default=None, help="覆盖 STUDIO_MCP_TRANSPORT")
    p.add_argument("--config", default=None, help="YAML 配置路径（默认取 STUDIO_MCP_CONFIG）")
    p.add_argument("--host", default=None, help="HTTP 模式监听地址")
    p.add_argument("--port", type=int, default=None, help="HTTP 模式监听端口")
    p.add_argument("--log-level", default=None, help="覆盖 STUDIO_MCP_LOG_LEVEL")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    settings = get_settings(args.config)

    if args.transport:
        settings.transport = args.transport
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port
    if args.log_level:
        settings.log_level = args.log_level

    # stdio: stdout is protocol — logging strictly to stderr
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("studiosystem_mcp")

    if settings.transport == "http":
        _run_http(settings, log)
    else:
        _run_stdio(settings, log)


def _run_stdio(settings, log: logging.Logger) -> None:
    mcp, ctx = build_server(settings)
    log.info("starting stdio transport (stdout reserved for protocol frames)")
    try:
        mcp.run(transport="stdio")
    finally:
        asyncio.run(ctx.aclose())


def _run_http(settings, log: logging.Logger) -> None:
    import uvicorn

    if not settings.mcp_token and not _is_loopback(settings.host) and not settings.insecure_dev_only:
        log.error(
            "HTTP 模式绑定 %s 但未设置 STUDIO_MCP_MCP_TOKEN。拒绝启动：请将 host 改为 127.0.0.1，"
            "或设置外层 Bearer token，或显式接受风险 STUDIO_MCP_INSECURE_DEV_ONLY=true",
            settings.host,
        )
        sys.exit(2)
    if not settings.mcp_token:
        log.warning("HTTP 模式未设置 STUDIO_MCP_MCP_TOKEN：仅允许回环访问（insecure_dev_only）")

    mcp, ctx = build_server(settings)
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    log.info(
        "starting streamable-http transport on http://%s:%s/mcp (stateless)", settings.host, settings.port
    )
    try:
        uvicorn.run(
            _wrap_with_auth(app, settings), host=settings.host, port=settings.port, log_level="warning"
        )
    finally:
        asyncio.run(ctx.aclose())


def _wrap_with_auth(app, settings):
    """Return an ASGI app enforcing the outer bearer token (if configured)."""
    from starlette.responses import JSONResponse

    token = settings.mcp_token

    async def asgi(scope, receive, send):
        if scope["type"] == "http" and token:
            headers = dict((k.decode(), v.decode()) for k, v in scope.get("headers", []))
            if headers.get("authorization") != f"Bearer {token}":
                resp = JSONResponse({"error": "unauthorized"}, status_code=401)
                await resp(scope, receive, send)
                return
        await app(scope, receive, send)

    return asgi


if __name__ == "__main__":
    main()
