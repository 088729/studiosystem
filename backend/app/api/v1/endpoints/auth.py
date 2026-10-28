from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_perm
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.services.auth import login_user, register_user
from app.services.permission import get_role_permissions_map, compute_permissions

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    result = await login_user(data.username, data.password, data.remember_me)
    return TokenResponse(**result)


@router.post("/register", response_model=UserInfo)
async def register(data: RegisterRequest):
    user = await register_user(
        username=data.username,
        password=data.password,
        full_name=data.full_name,
        email=data.email,
        department=data.department,
    )
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


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user)):
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


@router.get("/user/{username}", response_model=UserInfo)
async def get_user(username: str, current_user: User = Depends(get_current_user)):
    user = await User.find_one(User.username == username)
    if user is None:
        from app.core.exceptions import not_found
        raise not_found("user_not_found", "用户不存在")
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


@router.post("/verify")
async def verify_token(token_data: Dict[str, Any]):
    from app.core.security import decode_token
    try:
        payload = decode_token(token_data["token"])
        return {"valid": True, "payload": payload}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.get("/permissions")
async def list_permission_keys(current_user: User = Depends(get_current_user)):
    from app.models.user import SsoPlatformConfig

    config = await SsoPlatformConfig.find_one()
    if config is None:
        return {"items": []}
    return {"items": [item.model_dump() for item in config.permission_keys]}
