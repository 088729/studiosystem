from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.core.exceptions import bad_request, not_found, forbidden
from app.models.user import Role, User
from app.schemas.auth import RoleCreateUpdate

router = APIRouter()


@router.get("", response_model=List[RoleCreateUpdate])
async def list_roles(current_user: User = Depends(require_perm("sys:manage"))):
    roles = await Role.find_all().to_list()
    return [
        RoleCreateUpdate(
            name=role.name,
            permissions=role.permissions,
            description=role.description,
        )
        for role in roles
    ]


@router.post("", response_model=RoleCreateUpdate)
async def create_role(
    data: RoleCreateUpdate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    existing = await Role.find_one(Role.name == data.name)
    if existing is not None:
        raise bad_request("role_exists", "角色已存在")
    role = Role(
        name=data.name,
        permissions=data.permissions,
        description=data.description,
    )
    await role.insert()
    return data


@router.patch("/{name}", response_model=RoleCreateUpdate)
async def update_role(
    name: str,
    data: RoleCreateUpdate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    role = await Role.find_one(Role.name == name)
    if role is None:
        raise not_found("role_not_found", "角色不存在")
    if role.is_builtin:
        raise forbidden("内置角色不可编辑")
    role.permissions = data.permissions
    role.description = data.description
    await role.save()
    return RoleCreateUpdate(
        name=role.name,
        permissions=role.permissions,
        description=role.description,
    )


@router.delete("/{name}")
async def delete_role(
    name: str,
    current_user: User = Depends(require_perm("sys:manage")),
):
    role = await Role.find_one(Role.name == name)
    if role is None:
        raise not_found("role_not_found", "角色不存在")
    if role.is_builtin:
        raise forbidden("内置角色不可删除")

    users_with_role = await User.find(User.role_name == name).count()
    if users_with_role > 0:
        raise bad_request("role_in_use", f"仍有 {users_with_role} 个用户引用该角色")

    await role.delete()
    return {"message": "已删除"}
