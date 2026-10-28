import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_perm
from app.core.exceptions import bad_request, not_found, forbidden
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.auth import (
    UserInfo,
    UserCreate,
    UserPermissionUpdate,
    UserActiveUpdate,
    UserJobScopeUpdate,
    BatchPermissionsApply,
)
from app.services.permission import get_role_permissions_map, compute_permissions

router = APIRouter()


async def build_user_info(user: User) -> UserInfo:
    role_permissions_map = await get_role_permissions_map()
    perms = compute_permissions(
        user.role_name,
        user.extra_permissions,
        user.denied_permissions,
        role_permissions_map,
    )
    return UserInfo(
        username=user.username,
        role_name=user.role_name,
        perms=perms,
        full_name=user.full_name,
        email=user.email,
        department=user.department,
        job_scope=user.job_scope,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("", response_model=List[UserInfo])
async def list_users(
    q: Optional[str] = None,
    current_user: User = Depends(require_perm("sys:manage")),
):
    query = {}
    if q:
        query["$or"] = [
            {"username": {"$regex": re.escape(q), "$options": "i"}},
            {"full_name": {"$regex": re.escape(q), "$options": "i"}},
        ]
    users = await User.find(query).to_list()
    return [await build_user_info(user) for user in users]


@router.post("", response_model=UserInfo)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    existing = await User.find_one(User.username == data.username)
    if existing is not None:
        raise bad_request("user_exists", "用户已存在")

    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        role_name=data.role_name,
        full_name=data.full_name,
        email=data.email,
        department=data.department,
        job_scope=data.job_scope,
        is_active=data.is_active,
    )
    await user.insert()
    return await build_user_info(user)


@router.patch("/{username}/permissions", response_model=UserInfo)
async def update_user_permissions(
    username: str,
    data: UserPermissionUpdate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    user = await User.find_one(User.username == username)
    if user is None:
        raise not_found("user_not_found", "用户不存在")

    user.role_name = data.role_name
    user.extra_permissions = data.extra
    user.denied_permissions = data.denied
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    return await build_user_info(user)


@router.post("/batch-permissions")
async def batch_update_permissions(
    data: BatchPermissionsApply,
    current_user: User = Depends(require_perm("sys:manage")),
):
    updated = []
    for username in data.usernames:
        user = await User.find_one(User.username == username)
        if user is None:
            continue
        user.role_name = data.role_name
        user.extra_permissions = data.extra
        user.denied_permissions = data.denied
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        updated.append(username)
    return {"updated": updated}


@router.patch("/{username}/active", response_model=UserInfo)
async def set_user_active(
    username: str,
    data: UserActiveUpdate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    user = await User.find_one(User.username == username)
    if user is None:
        raise not_found("user_not_found", "用户不存在")
    user.is_active = data.is_active
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    return await build_user_info(user)


@router.patch("/{username}/job-scope", response_model=UserInfo)
async def update_job_scope(
    username: str,
    data: UserJobScopeUpdate,
    current_user: User = Depends(get_current_user),
):
    from app.services.permission import compute_permissions

    perms = compute_permissions(
        current_user.role_name,
        current_user.extra_permissions,
        current_user.denied_permissions,
        await get_role_permissions_map(),
    )
    if current_user.username != username and "*" not in perms and "sys:manage" not in perms:
        raise forbidden("只能修改自己的工作职能")

    user = await User.find_one(User.username == username)
    if user is None:
        raise not_found("user_not_found", "用户不存在")
    user.job_scope = data.job_scope
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    return await build_user_info(user)


@router.delete("/{username}")
async def delete_user(
    username: str,
    current_user: User = Depends(require_perm("sys:manage")),
):
    user = await User.find_one(User.username == username)
    if user is None:
        raise not_found("user_not_found", "用户不存在")
    await user.delete()
    return {"message": "已删除"}
