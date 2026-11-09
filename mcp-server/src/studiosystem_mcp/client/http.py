"""HTTP layer: StudioClient — token injection, 401 re-login + single retry,
bounded retry on transient 5xx/transport errors for idempotent methods,
error normalization."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..errors import StudioError, error_from_response
from ..settings import Settings
from .auth import AuthProvider, build_auth

logger = logging.getLogger(__name__)

IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}
TRANSIENT_STATUSES = set(range(500, 600))


class _Unauthorized(Exception):
    """Internal control-flow marker for 401."""


class StudioClient:
    """Async REST client for the Studio backend `/api/v1`."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.api_base,
            timeout=httpx.Timeout(settings.timeout),
            transport=transport,
        )
        self._auth: AuthProvider = build_auth(settings, self._client)

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- auth --

    async def _headers(self) -> dict[str, str]:
        token = await self._auth.get_token()
        return {"Authorization": f"Bearer {token}"}

    # -- request core --

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        """Perform a request.

        - 401 → refresh credentials (re-login) and retry exactly once.
        - Idempotent methods (GET…) → bounded retry on transient 5xx /
          transport errors per STUDIO_MCP_RETRY.
        - Any remaining 4xx/5xx → normalized StudioError.
        """
        max_transient = self.settings.retry if method in IDEMPOTENT_METHODS else 0
        retried_auth = False
        transient_retries = 0

        while True:
            try:
                resp = await self._client.request(
                    method, path, params=params, json=json, headers=await self._headers()
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if transient_retries < max_transient:
                    transient_retries += 1
                    logger.warning(
                        "studio %s %s transport error: %s (retry %s)", method, path, exc, transient_retries
                    )
                    continue
                raise StudioError(
                    "backend_unreachable",
                    f"无法连接后端: {exc}",
                    hint="检查 STUDIO_BASE_URL 与网络，确认后端服务已启动",
                ) from exc

            if resp.status_code == 401 and not retried_auth:
                retried_auth = True
                logger.info("studio token rejected (401), re-login and retry once")
                await self._auth.refresh()
                continue

            if resp.status_code in TRANSIENT_STATUSES and transient_retries < max_transient:
                transient_retries += 1
                logger.warning(
                    "studio %s %s → %s (retry %s)", method, path, resp.status_code, transient_retries
                )
                continue

            if resp.status_code >= 400:
                try:
                    payload: Any = resp.json()
                except Exception:
                    payload = None
                raise error_from_response(resp.status_code, payload)
            break

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # convenience wrappers

    async def get(self, path: str, *, params: dict | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, *, json: Any = None, params: dict | None = None) -> Any:
        return await self.request("POST", path, json=json, params=params)

    async def patch(self, path: str, *, json: Any = None, params: dict | None = None) -> Any:
        return await self.request("PATCH", path, json=json, params=params)

    async def put(self, path: str, *, json: Any = None, params: dict | None = None) -> Any:
        return await self.request("PUT", path, json=json, params=params)

    async def delete(self, path: str, *, params: dict | None = None) -> Any:
        return await self.request("DELETE", path, params=params)
