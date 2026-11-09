"""Settings precedence tests: env > YAML > defaults; redaction; module parsing."""

import os

import pytest

from studiosystem_mcp.settings import get_settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in list(os.environ):
        if var.startswith("STUDIO_MCP_"):
            monkeypatch.delenv(var, raising=False)
    reset_settings_cache()
    yield
    reset_settings_cache()


class TestDefaults:
    def test_builtins(self):
        s = get_settings(None)
        assert s.studio_base_url == "http://127.0.0.1:8302"
        assert s.enabled_modules == frozenset({"case", "task", "wiki"})
        assert s.version_list == ["2026-07-28", "2025-11-25"]
        assert s.read_only is False

    def test_api_prefix_stripped(self, monkeypatch):
        monkeypatch.setenv("STUDIO_MCP_STUDIO_BASE_URL", "http://example.com:8302/api/v1/")
        reset_settings_cache()
        assert get_settings(None).api_base == "http://example.com:8302/api/v1"


class TestEnvOverridesYaml:
    def test_yaml_loads(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            """
studio:
  base_url: "http://yaml-host:8302"
modules:
  enabled: ["case", "wiki"]
  read_only: true
""",
            encoding="utf-8",
        )
        s = get_settings(str(cfg))
        assert s.studio_base_url == "http://yaml-host:8302"
        assert s.enabled_modules == frozenset({"case", "wiki"})
        assert s.read_only is True

    def test_env_beats_yaml(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text('studio:\n  base_url: "http://yaml-host:8302"\n', encoding="utf-8")
        monkeypatch.setenv("STUDIO_MCP_STUDIO_BASE_URL", "http://env-host:8302")
        reset_settings_cache()
        assert get_settings(str(cfg)).studio_base_url == "http://env-host:8302"


class TestRedaction:
    def test_secrets_masked(self):
        s = get_settings(None)
        s.password = "super-secret"
        s.token = "abcd1234"
        s.mcp_token = "tok"
        data = s.redacted()
        assert data["password"] == "***cret"
        assert data["token"] == "***1234"
        assert data["mcp_token"] == "***"
        assert data["username"] is None or isinstance(data["username"], str)


class TestGuardIntegration:
    def test_module_filter(self, monkeypatch):
        monkeypatch.setenv("STUDIO_MCP_MODULES", "case")
        reset_settings_cache()
        from studiosystem_mcp.policy.guard import ToolGuard

        guard = ToolGuard(get_settings(None))
        assert guard.register.__self__ is guard
        from studiosystem_mcp.tools import TOOL_METAS

        accepted = [m for m in TOOL_METAS if guard.register(m)]
        domains = {m.domain for m in accepted}
        assert domains == {"system", "case"}
