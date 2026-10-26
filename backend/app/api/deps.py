from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import unauthorized, forbidden
from app.core.security import decode_token
from app.models.user import User
from app.services.auth import get_user_permissions
from app.services.permission import get_role_permissions_map, compute_permissions

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/common/auth/login", auto_error=False)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    if not token:
        raise unauthorized()
    try:
        payload = decode_token(token)
    except Exception:
        raise unauthorized("token 无效或已过期")

    username: Optional[str] = payload.get("sub")
    if username is None:
        raise unauthorized("token 格式错误")

    user = await User.find_one(User.username == username)
    if user is None:
        raise unauthorized("用户不存在")
    if not user.is_active:
        raise forbidden("账号已禁用")
    return user


async def get_global_perms(user: User) -> set:
    """用户全局权限（角色 + 个人增减）。"""
    role_permissions_map = await get_role_permissions_map()
    return compute_permissions(
        user.role_name,
        user.extra_permissions,
        user.denied_permissions,
        role_permissions_map,
    )


async def has_perm(user: User, perm: str) -> bool:
    """全局权限（角色 + 个人增减）。"""
    perms = await get_global_perms(user)
    if "*" in perms or perm in perms:
        return True
    return False


def require_perm(perm: str):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if await has_perm(user, perm):
            return user
        raise forbidden(f"缺少权限: {perm}")

    return _checker
