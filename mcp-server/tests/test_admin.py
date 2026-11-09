"""P3 admin domain tests: triple gating, confirm flows, self-protection, audit masking."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.server import build_server

ADMIN_MODULES = "admin"


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(
            audit_file=str(tmp_path / "audit.jsonl"),
            modules=ADMIN_MODULES,
            allow_admin=True,
        ),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


async def _confirm_and_run(mcp, tool, args):
    first = json.loads((await mcp.call_tool(tool, args)).content[0].text)
    assert first["requires_confirmation"] is True, first
    return json.loads(
        (await mcp.call_tool(tool, {**args, "confirm_token": first["confirm_token"]})).content[0].text
    )


class TestGating:
    async def test_default_off_no_admin_tools(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(modules=ADMIN_MODULES), transport=mock_transport
        )
        try:
            names = [t.name for t in await mcp.list_tools()]
            assert not any(n.startswith("admin_") for n in names)
        finally:
            await ctx.aclose()

    async def test_read_only_disables_admin_even_with_flag(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(modules=ADMIN_MODULES, allow_admin=True, read_only=True),
            transport=mock_transport,
        )
        try:
            names = [t.name for t in await mcp.list_tools()]
            assert not any(n.startswith("admin_") for n in names)
        finally:
            await ctx.aclose()

    async def test_enabled_lists_all_admin_tools(self, mcp_ctx):
        mcp, _ = mcp_ctx
        names = {t.name for t in await mcp.list_tools()}
        admin_names = {n for n in names if n.startswith("admin_")}
        assert len(admin_names) == 12

    async def test_denied_tools_can_block_single_admin_tool(self, mock_transport):
        mcp, ctx = build_server(
            make_settings(
                modules=ADMIN_MODULES,
                allow_admin=True,
                denied_tools="admin_user_delete",
            ),
            transport=mock_transport,
        )
        try:
            names = {t.name for t in await mcp.list_tools()}
            assert "admin_user_delete" not in names
            assert "admin_user_list" in names
        finally:
            await ctx.aclose()


class TestUserAdmin:
    async def test_list_users(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("admin_user_list", {})).content[0].text)
        assert payload["ok"] is True and payload["count"] == 2

    async def test_create_user_confirm_flow_and_audit_masking(self, mcp_ctx, fake_backend, tmp_path):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "admin_user_create",
            {
                "username": "bot2",
                "password": "Sup3rSecret!",
                "role_name": "viewer",
                "full_name": "二号机",
            },
        )
        assert result["ok"] is True
        assert result["user"]["username"] == "bot2"
        assert "perms" not in result["user"]
        assert "password" not in result["user"]
        # 审计日志不得出现密码明文
        audit_text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
        assert "Sup3rSecret!" not in audit_text
        assert '"password": "***"' in audit_text

    async def test_create_user_short_password_rejected(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "admin_user_create", {"username": "x", "password": "short"}
            )
        assert "至少 8 位" in str(ei.value)

    async def test_update_permissions(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "admin_user_update",
            {
                "username": "tester",
                "action": "permissions",
                "role_name": "viewer",
                "extra": ["task:edit"],
            },
        )
        assert result["ok"] is True
        assert fake_backend.users["tester"]["role_name"] == "viewer"

    async def test_cannot_deactivate_self(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "admin_user_update",
                {"username": "mcp-bot", "action": "active", "is_active": False},
            )
        assert "锁在门外" in str(ei.value)

    async def test_cannot_delete_self(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await mcp.call_tool("admin_user_delete", {"username": "mcp-bot"})
        assert "不能删除当前登录账号" in str(ei.value)

    async def test_delete_other_user(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(mcp, "admin_user_delete", {"username": "tester"})
        assert result["ok"] is True and result["deleted"] is True
        assert "tester" not in fake_backend.users

    async def test_batch_permissions(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = await _confirm_and_run(
            mcp,
            "admin_batch_permissions",
            {"usernames": ["mcp-bot", "tester"], "role_name": "tester"},
        )
        assert result["ok"] is True
        assert result["result"]["updated"] == ["mcp-bot", "tester"]
        assert fake_backend.users["mcp-bot"]["role_name"] == "tester"


class TestRoleAdmin:
    async def test_role_list(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("admin_role_list", {})).content[0].text)
        assert payload["count"] == 2

    async def test_create_and_update_role(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        created = await _confirm_and_run(
            mcp, "admin_role_create", {"name": "ops", "permissions": ["task:view"], "description": "运维"}
        )
        assert created["ok"] is True and "ops" in fake_backend.roles

        updated = await _confirm_and_run(
            mcp,
            "admin_role_update",
            {"name": "ops", "permissions": ["task:view", "wiki:view"], "description": "运维+知识库"},
        )
        assert updated["ok"] is True
        assert fake_backend.roles["ops"]["permissions"] == ["task:view", "wiki:view"]

    async def test_builtin_role_protected_by_backend(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await _confirm_and_run(
                mcp, "admin_role_delete", {"name": "viewer"}
            )
        assert "内置角色不可删除" in str(ei.value)

    async def test_delete_role_in_use_rejected(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await _confirm_and_run(mcp, "admin_role_delete", {"name": "tester"})
        assert "引用" in str(ei.value)


class TestPermissionKeys:
    async def test_list(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads(
            (await mcp.call_tool("admin_permission_list", {})).content[0].text
        )
        assert payload["count"] == 2

    async def test_create_and_delete(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        created = await _confirm_and_run(
            mcp, "admin_permission_create", {"key": "task:export", "app_id": "task"}
        )
        assert created["ok"] is True
        assert any(p["key"] == "task:export" for p in fake_backend.permission_keys)

        deleted = await _confirm_and_run(
            mcp, "admin_permission_delete", {"key": "task:export"}
        )
        assert deleted["ok"] is True
        assert all(p["key"] != "task:export" for p in fake_backend.permission_keys)

    async def test_builtin_key_delete_rejected(self, mcp_ctx):
        mcp, _ = mcp_ctx
        with pytest.raises(Exception) as ei:
            await _confirm_and_run(mcp, "admin_permission_delete", {"key": "task:view"})
        assert "内置" in str(ei.value)
