"""Configuration: three layers — env vars (STUDIO_MCP_*) / .env > YAML config > defaults.

Priority (pydantic-settings custom sources, first = highest):
  init kwargs > environment > dotenv > file secrets > YAML config file > defaults
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

ALL_MODULES = (
    "case",
    "task",
    "wiki",
    "focus",
    "habits",
    "analytics",
    "git",
    "collab",
    "admin",
    "workflow",
    "scheduler",
)

CORE_MODULES = ("case", "task", "wiki")


class Settings(BaseSettings):
    """Runtime settings. Every field maps 1:1 to a STUDIO_MCP_* env var."""

    model_config = SettingsConfigDict(
        env_prefix="STUDIO_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- backend ---
    studio_base_url: str = "http://127.0.0.1:8302"

    # --- auth ---
    auth_mode: str = "password"  # password | bearer | pat
    username: str | None = None
    password: str | None = None
    token: str | None = None
    token_file: str | None = None
    pat: str | None = None

    # --- transport ---
    transport: str = "stdio"  # stdio | http
    host: str = "127.0.0.1"
    port: int = 8303
    mcp_token: str | None = None  # outer bearer for HTTP transport (shared secret)
    insecure_dev_only: bool = False  # explicitly accept non-loopback HTTP without a token

    # --- modules / policy ---
    modules: str = "case,task,wiki"
    read_only: bool = False
    allowed_tools: str | None = None  # comma-separated
    denied_tools: str | None = None
    confirm_mode: str = "auto"  # auto | token | none
    allow_destructive: bool = False
    allow_admin: bool = False  # admin 域总开关：仍需 READ_ONLY=false + 后端 sys:manage
    rate_limit_per_minute: int = 30  # 令牌桶；<=0 关闭（防模型循环调用打爆后端）

    # --- protocol ---
    protocol_versions: str = "2026-07-28,2025-11-25"
    tool_ttl_ms: int = 60000

    # --- behavior ---
    case_source: str = "published"  # published | draft
    default_vault_id: str | None = None
    default_wiki_path: str = "reports/{date}.md"
    templates_dir: str | None = None
    timeout: float = 15.0
    retry: int = 2
    tz_offset_minutes: int = 480
    max_result_items: int = 20

    # --- logging ---
    log_level: str = "INFO"
    audit_file: str | None = None

    @field_validator("studio_base_url")
    @classmethod
    def _strip_api_prefix(cls, v: str) -> str:
        v = v.rstrip("/")
        if v.endswith("/api/v1"):
            v = v[: -len("/api/v1")]
        return v

    @field_validator("auth_mode", "transport", "confirm_mode", "case_source")
    @classmethod
    def _check_literals(cls, v: str, info) -> str:
        allowed = {
            "auth_mode": {"password", "bearer", "pat"},
            "transport": {"stdio", "http"},
            "confirm_mode": {"auto", "token", "none"},
            "case_source": {"published", "draft"},
        }[info.field_name]
        if v not in allowed:
            raise ValueError(f"{info.field_name} must be one of {sorted(allowed)}, got {v!r}")
        return v

    # ----- derived helpers -----

    @property
    def api_base(self) -> str:
        return f"{self.studio_base_url}/api/v1"

    @property
    def enabled_modules(self) -> frozenset[str]:
        return frozenset(m.strip() for m in self.modules.split(",") if m.strip())

    @property
    def version_list(self) -> list[str]:
        return [v.strip() for v in self.protocol_versions.split(",") if v.strip()]

    @property
    def allowed_tool_set(self) -> frozenset[str] | None:
        return self._split(self.allowed_tools)

    @property
    def denied_tool_set(self) -> frozenset[str]:
        return self._split(self.denied_tools) or frozenset()

    @staticmethod
    def _split(value: str | None) -> frozenset[str] | None:
        if not value:
            return None
        return frozenset(t.strip() for t in value.split(",") if t.strip())

    def redacted(self) -> dict[str, Any]:
        """Config summary safe to expose via tools/resources (secrets masked)."""
        secret_keys = {"password", "token", "pat", "mcp_token"}
        data: dict[str, Any] = {}
        for key, value in self.model_dump().items():
            if key in secret_keys and value:
                s = str(value)
                data[key] = "***" + s[-4:] if len(s) >= 4 else "***"
            elif key == "token_file" and value:
                data[key] = "<set>"
            else:
                data[key] = value
        return data


class YamlConfigSource(PydanticBaseSettingsSource):
    """Lowest-priority source: defaults from a YAML file (STUDIO_MCP_CONFIG)."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_path: str | None):
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {}
        path = yaml_path or os.environ.get("STUDIO_MCP_CONFIG")
        if path and Path(path).is_file():
            raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            self._data = self._flatten(raw)

    @staticmethod
    def _flatten(raw: dict) -> dict[str, Any]:
        """Map config.example.yaml nesting onto flat Settings field names."""
        out: dict[str, Any] = {}
        if base := (raw.get("studio") or {}).get("base_url"):
            out["studio_base_url"] = base
        for k, v in (raw.get("auth") or {}).items():
            out[k] = v
        for k, v in (raw.get("transport") or {}).items():
            out[k] = v
        mods = raw.get("modules") or {}
        if enabled := mods.get("enabled"):
            out["modules"] = ",".join(str(m) for m in enabled)
        for k in ("read_only", "allowed_tools", "denied_tools", "confirm_mode", "allow_destructive", "allow_admin"):
            if k in mods:
                out[k] = mods[k]
        for k, v in (raw.get("protocol") or {}).items():
            out["protocol_versions" if k == "versions" else f"protocol_{k}"] = v
        for k, v in (raw.get("behavior") or {}).items():
            out[k] = v
        for k, v in (raw.get("logging") or {}).items():
            out[f"log_{k}" if k == "level" else f"audit_{k}"] = v
        return out

    def get_field_value(self, field, field_name: str):  # noqa: ANN001 - pydantic protocol
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if v is not None}


def _build(config_path: str | None = None) -> Settings:
    yaml_path = config_path  # captured for the custom source

    class _Settings(Settings):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ):
            yaml_source = YamlConfigSource(settings_cls, yaml_path)
            # first = highest priority; YAML sits below everything else
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
                yaml_source,
            )

    return _Settings()


@lru_cache(maxsize=1)
def get_settings(config_path: str | None = None) -> Settings:
    """Build settings once per process (YAML path included in cache key via args)."""
    return _build(config_path)


def reset_settings_cache() -> None:
    get_settings.cache_clear()
