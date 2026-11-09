"""Authentication providers: password (auto login) / bearer / pat.

Credentials never appear in logs, audit records, or tool results.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Protocol

import httpx

from ..settings import Settings

logger = logging.getLogger(__name__)


class AuthProvider(Protocol):
    """Supplies a bearer token for the Studio backend."""

    async def get_token(self) -> str: ...

    async def refresh(self) -> None: ...


class PasswordAuth:
    """Login with username/password, remember_me=true → long-lived JWT.

    Token cached in memory; `refresh()` re-logins. On 401 the HTTP layer calls
    refresh() once and retries the request.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client
        self._token: str | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._token:
            return self._token
        await self.refresh()
        assert self._token is not None
        return self._token

    async def refresh(self) -> None:
        s = self._settings
        if not s.username or not s.password:
            raise RuntimeError(
                "STUDIO_MCP_AUTH_MODE=password 需要 STUDIO_MCP_USERNAME 与 STUDIO_MCP_PASSWORD"
            )
        async with self._lock:
            resp = await self._client.post(
                f"{s.api_base}/common/auth/login",
                json={"username": s.username, "password": s.password, "remember_me": True},
            )
            if resp.status_code != 200:
                from .errors import error_from_response

                raise error_from_response(resp.status_code, resp.json())
            data = resp.json()
            self._token = data["access_token"]
            logger.info(
                "studio login ok: expires_in=%ss user=%s",
                data.get("expires_in"),
                s.username,
            )


class BearerAuth:
    """Use a long-lived JWT injected by the deployer (env or file)."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._token: str | None = None

    def _load(self) -> str:
        if self._token:
            return self._token
        s = self._settings
        if s.token_file:
            token = Path(s.token_file).read_text(encoding="utf-8").strip()
        elif s.token:
            token = s.token
        else:
            raise RuntimeError("STUDIO_MCP_AUTH_MODE=bearer 需要 STUDIO_MCP_TOKEN 或 STUDIO_MCP_TOKEN_FILE")
        if not token:
            raise RuntimeError("bearer token 为空")
        self._token = token
        return token

    async def get_token(self) -> str:
        return self._load()

    async def refresh(self) -> None:
        self._token = None
        self._load()  # re-read file in case the deployer rotated it


class PatAuth:
    """Personal Access Token (backend enhancement, P3).

    Until the backend ships PAT verification, the PAT is sent as a bearer
    token; the backend will accept it only if it is actually a JWT.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    async def get_token(self) -> str:
        if not self._settings.pat:
            raise RuntimeError("STUDIO_MCP_AUTH_MODE=pat 需要 STUDIO_MCP_PAT")
        return self._settings.pat

    async def refresh(self) -> None:  # nothing to refresh
        return None


def build_auth(settings: Settings, client: httpx.AsyncClient) -> AuthProvider:
    if settings.auth_mode == "password":
        return PasswordAuth(settings, client)
    if settings.auth_mode == "bearer":
        return BearerAuth(settings)
    if settings.auth_mode == "pat":
        return PatAuth(settings)
    raise RuntimeError(f"未知 auth_mode: {settings.auth_mode}")
