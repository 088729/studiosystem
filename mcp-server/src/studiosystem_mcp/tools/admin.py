"""Admin domain (P3, default OFF): user / role / permission-key management.

Triple-gated per plan §9: the whole domain only registers when
`STUDIO_MCP_ALLOW_ADMIN=true` **and** `READ_ONLY=false`; the backend still
enforces `sys:manage` on every endpoint. Every write goes through the forced
confirmation gate, and the audit wrapper masks credential arguments.

Extra client-side guardrails (backend has none):
- refusing to delete or deactivate the currently authenticated user;
- never echoing passwords in previews or results.
"""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..context import AppContext
from ..policy.flow import confirm_gate

USERS = "/common/auth/users"
ROLES = "/common/auth/roles"
PERMS = "/common/platform/permissions"


async def _me(ctx: AppContext) -> str:
    me = await ctx.client.get("/common/auth/me")
    return str(me.get("username") or "")


def register(mcp, ctx: AppContext) -> None:

    # ---------------- read-only ----------------

    @mcp.tool(
        name="admin_user_list",
        description="列出用户（用户名/角色/生效权限/部门/激活状态）。需要后端 sys:manage 权限。",
    )
    async def admin_user_list(q: str | None = None) -> dict:
        try:
            params = {"q": q} if q else None
            users = await ctx.client.get(USERS, params=params)
            return {"ok": True, "count": len(users or []), "users": users or []}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_role_list",
        description="列出角色及其权限键。需要后端 sys:manage 权限。",
    )
    async def admin_role_list() -> dict:
        try:
            roles = await ctx.client.get(ROLES)
            return {"ok": True, "count": len(roles or []), "roles": roles or []}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_permission_list",
        description="列出平台权限键（含内置标记）。普通登录用户即可调用。",
    )
    async def admin_permission_list() -> dict:
        try:
            data = await ctx.client.get(f"{PERMS}")
            items = data.get("items", [])
            return {"ok": True, "count": len(items), "permissions": items}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- user writes (all forced-confirm) ----------------

    @mcp.tool(
        name="admin_user_create",
        description=(
            "创建用户（强制确认）。password 只出现在本参数中，不会回显、不进审计明文。"
            "建议专用最小权限账号，角色用 viewer 起步按需加 extra 权限。"
        ),
    )
    async def admin_user_create(
        username: str,
        password: str,
        role_name: str = "viewer",
        full_name: str | None = None,
        email: str | None = None,
        department: str | None = None,
        job_scope: str | None = None,
        is_active: bool = True,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if len(password) < 8:
                raise ToolError("password 至少 8 位")
            payload: dict = {
                "username": username,
                "password": password,
                "role_name": role_name,
                "is_active": is_active,
            }
            for key, val in (
                ("full_name", full_name),
                ("email", email),
                ("department", department),
                ("job_scope", job_scope),
            ):
                if val is not None:
                    payload[key] = val
            preview = {"username": username, "role_name": role_name, "is_active": is_active, "password": "***"}

            async def execute(_args: dict) -> dict:
                user = await ctx.client.post(USERS, json=payload)
                user.pop("perms", None)  # 权限列表可能很长，创建结果里略去
                return {"ok": True, "user": user}

            return await confirm_gate(
                ctx,
                "admin_user_create",
                {
                    "username": username,
                    "password": "***",
                    "role_name": role_name,
                    "confirm_token": confirm_token,
                    "dry_run": dry_run,
                },
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_user_update",
        description=(
            "修改用户（强制确认）。action: permissions(角色+额外/拒绝权限) / active(启用停用) / job_scope(工作职能)。"
            "不允许停用当前登录账号自己。"
        ),
    )
    async def admin_user_update(
        username: str,
        action: str,
        role_name: str | None = None,
        extra: list[str] | None = None,
        denied: list[str] | None = None,
        is_active: bool | None = None,
        job_scope: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if action == "permissions":
                if not role_name:
                    raise ToolError("action=permissions 需要 role_name")
                path, payload = f"{USERS}/{username}/permissions", {
                    "role_name": role_name,
                    "extra": extra or [],
                    "denied": denied or [],
                }
                preview = {"username": username, "action": action, **payload}
            elif action == "active":
                if is_active is None:
                    raise ToolError("action=active 需要 is_active 参数")
                if not is_active and username == await _me(ctx):
                    raise ToolError("不能停用当前登录账号（会把自己锁在门外）")
                path, payload = f"{USERS}/{username}/active", {"is_active": is_active}
                preview = {"username": username, "action": action, **payload}
            elif action == "job_scope":
                if job_scope is None:
                    raise ToolError("action=job_scope 需要 job_scope 参数")
                path, payload = f"{USERS}/{username}/job-scope", {"job_scope": job_scope}
                preview = {"username": username, "action": action, **payload}
            else:
                raise ToolError(f"未知 action: {action}（可用 permissions/active/job_scope）")

            async def execute(_args: dict) -> dict:
                user = await ctx.client.patch(path, json=payload)
                user.pop("perms", None)
                return {"ok": True, "user": user}

            return await confirm_gate(
                ctx,
                "admin_user_update",
                {"username": username, "action": action, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_user_delete",
        description="删除用户（强制确认，不可恢复）。不允许删除当前登录账号自己。",
    )
    async def admin_user_delete(
        username: str,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if username == await _me(ctx):
                raise ToolError("不能删除当前登录账号")
            preview = {"username": username, "recoverable": False, "warning": "用户删除后无法恢复"}

            async def execute(_args: dict) -> dict:
                await ctx.client.delete(f"{USERS}/{username}")
                return {"ok": True, "username": username, "deleted": True}

            return await confirm_gate(
                ctx,
                "admin_user_delete",
                {"username": username, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_batch_permissions",
        description="批量套用角色/权限到多个用户（强制确认）。适合按团队统一调整。",
    )
    async def admin_batch_permissions(
        usernames: list[str],
        role_name: str,
        extra: list[str] | None = None,
        denied: list[str] | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if not usernames:
                raise ToolError("usernames 不能为空")
            payload = {"usernames": usernames, "role_name": role_name, "extra": extra or [], "denied": denied or []}
            preview = {"affected": len(usernames), **payload}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(f"{USERS}/batch-permissions", json=payload)
                return {"ok": True, "result": result}

            return await confirm_gate(
                ctx,
                "admin_batch_permissions",
                {"usernames": usernames, "role_name": role_name, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- role writes ----------------

    @mcp.tool(
        name="admin_role_create",
        description="创建角色（强制确认）：名称 + 权限键列表 + 描述。",
    )
    async def admin_role_create(
        name: str,
        permissions: list[str] | None = None,
        description: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            payload: dict = {"name": name, "permissions": permissions or []}
            if description is not None:
                payload["description"] = description
            preview = dict(payload)

            async def execute(_args: dict) -> dict:
                role = await ctx.client.post(ROLES, json=payload)
                return {"ok": True, "role": role}

            return await confirm_gate(
                ctx,
                "admin_role_create",
                {"name": name, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_role_update",
        description="更新角色权限（强制确认）。内置角色会被后端拒绝。",
    )
    async def admin_role_update(
        name: str,
        permissions: list[str] | None = None,
        description: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            payload: dict = {"name": name, "permissions": permissions or []}
            if description is not None:
                payload["description"] = description
            preview = dict(payload)

            async def execute(_args: dict) -> dict:
                role = await ctx.client.patch(f"{ROLES}/{name}", json=payload)
                return {"ok": True, "role": role}

            return await confirm_gate(
                ctx,
                "admin_role_update",
                {"name": name, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_role_delete",
        description="删除角色（强制确认）。内置角色或被用户引用的角色会被后端拒绝。",
    )
    async def admin_role_delete(
        name: str,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            preview = {"name": name, "recoverable": False, "warning": "删除前请确认没有用户引用该角色"}

            async def execute(_args: dict) -> dict:
                await ctx.client.delete(f"{ROLES}/{name}")
                return {"ok": True, "name": name, "deleted": True}

            return await confirm_gate(
                ctx,
                "admin_role_delete",
                {"name": name, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- permission key writes ----------------

    @mcp.tool(
        name="admin_permission_create",
        description="新增平台权限键（强制确认）。key 建议带域前缀（如 task:export）。",
    )
    async def admin_permission_create(
        key: str,
        app_id: str | None = None,
        builtin: bool = False,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            payload: dict = {"key": key, "builtin": builtin}
            if app_id is not None:
                payload["app_id"] = app_id
            preview = dict(payload)

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(f"{PERMS}", json=payload)
                return {"ok": True, "result": result}

            return await confirm_gate(
                ctx,
                "admin_permission_create",
                {"key": key, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="admin_permission_delete",
        description="删除平台权限键（强制确认）。内置权限键会被后端拒绝。",
    )
    async def admin_permission_delete(
        key: str,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            preview = {"key": key, "recoverable": False}

            async def execute(_args: dict) -> dict:
                await ctx.client.delete(f"{PERMS}/{key}")
                return {"ok": True, "key": key, "deleted": True}

            return await confirm_gate(
                ctx,
                "admin_permission_delete",
                {"key": key, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except Exception as exc:
            raise ToolError(str(exc)) from exc
