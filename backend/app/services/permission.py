from typing import List, Set

from app.models.user import Role, SsoPlatformConfig, PermissionKeyItem


BUILTIN_PERMISSION_KEYS = [
    PermissionKeyItem(key="xmind:view", builtin=True),
    PermissionKeyItem(key="xmind:edit", builtin=True),
    PermissionKeyItem(key="xmind:delete", builtin=True),
    PermissionKeyItem(key="xmind:manage", builtin=True),
    PermissionKeyItem(key="wiki:view", builtin=True),
    PermissionKeyItem(key="wiki:edit", builtin=True),
    PermissionKeyItem(key="wiki:delete", builtin=True),
    PermissionKeyItem(key="wiki:manage", builtin=True),
    PermissionKeyItem(key="sys:manage", builtin=True),
    PermissionKeyItem(key="task:view", builtin=True),
    PermissionKeyItem(key="task:create", builtin=True),
    PermissionKeyItem(key="task:edit", builtin=True),
    PermissionKeyItem(key="task:delete", builtin=True),
    PermissionKeyItem(key="task:run", builtin=True),
    PermissionKeyItem(key="task:manage", builtin=True),
    PermissionKeyItem(key="task:share", builtin=True),
]

BUILTIN_ROLES = [
    {
        "name": "admin",
        "permissions": ["*"],
        "description": "超级管理员",
        "is_builtin": True,
    },
    {
        "name": "tester",
        "permissions": ["xmind:view", "xmind:edit", "xmind:delete", "wiki:view", "wiki:edit", "wiki:delete", "task:view", "task:create", "task:run", "task:share"],
        "description": "测试人员",
        "is_builtin": True,
    },
    {
        "name": "developer",
        "permissions": ["xmind:view", "wiki:view", "task:view"],
        "description": "开发人员",
        "is_builtin": True,
    },
    {
        "name": "viewer",
        "permissions": ["xmind:view", "wiki:view", "task:view"],
        "description": "只读用户",
        "is_builtin": True,
    },
]


def compute_permissions(
    role_name: str,
    extra_permissions: List[str],
    denied_permissions: List[str],
    role_permissions_map: dict[str, List[str]],
) -> List[str]:
    base = set(role_permissions_map.get(role_name, []))
    extra = set(extra_permissions)
    denied = set(denied_permissions)

    if "*" in base or "*" in extra:
        return ["*"]

    perms: Set[str] = (base | extra) - denied
    return sorted(list(perms))


async def ensure_platform_config() -> None:
    config = await SsoPlatformConfig.find_one()
    if config is None:
        config = SsoPlatformConfig(permission_keys=list(BUILTIN_PERMISSION_KEYS))
        await config.insert()
        return

    existing_keys = {item.key for item in config.permission_keys}
    for item in BUILTIN_PERMISSION_KEYS:
        if item.key not in existing_keys:
            config.permission_keys.append(item)
    await config.save()


async def ensure_builtin_roles() -> None:
    for role_data in BUILTIN_ROLES:
        existing = await Role.find_one(Role.name == role_data["name"])
        if existing is None:
            role = Role(**role_data)
            await role.insert()
        elif existing.is_builtin:
            # 仅增量补齐：老库中已存在的内置角色获得新增的内置权限（不改用户自定义角色）
            builtin_perms = {p for r in BUILTIN_ROLES if r["name"] == existing.name for p in r["permissions"]}
            missing = builtin_perms - set(existing.permissions)
            if missing and "*" not in existing.permissions:
                existing.permissions = sorted(set(existing.permissions) | builtin_perms)
                await existing.save()


async def init_permissions() -> None:
    await ensure_platform_config()
    await ensure_builtin_roles()


async def get_role_permissions_map() -> dict[str, List[str]]:
    roles = await Role.find_all().to_list()
    return {role.name: role.permissions for role in roles}
