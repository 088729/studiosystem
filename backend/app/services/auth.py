from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.exceptions import unauthorized, forbidden, bad_request
from app.models.user import User
from app.services.permission import compute_permissions, get_role_permissions_map


async def register_user(
    username: str,
    password: str,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    department: Optional[str] = None,
) -> User:
    existing = await User.find_one(User.username == username)
    if existing is not None:
        raise bad_request("user_exists", "用户名已存在")

    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        role_name="viewer",
        full_name=full_name,
        email=email,
        department=department,
        is_active=True,
    )
    await user.insert()
    return user


async def authenticate_user(username: str, password: str) -> Optional[User]:
    user = await User.find_one(User.username == username)
    if user is None:
        return None
    if user.hashed_password is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def login_user(username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
    user = await authenticate_user(username, password)
    if user is None:
        raise unauthorized("用户名或密码错误")

    role_permissions_map = await get_role_permissions_map()
    perms = compute_permissions(
        user.role_name,
        user.extra_permissions,
        user.denied_permissions,
        role_permissions_map,
    )

    user.last_login_at = datetime.now(timezone.utc)
    await user.save()

    settings = get_settings()
    if remember_me:
        expires_delta = timedelta(days=settings.long_token_expire_days)
        expires_in = settings.long_token_expire_days * 24 * 60 * 60
    else:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        expires_in = settings.access_token_expire_minutes * 60

    token = create_access_token(
        data={"sub": user.username, "role_name": user.role_name, "perms": perms},
        expires_delta=expires_delta,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


async def sync_user(username: str) -> User:
    user = await User.find_one(User.username == username)
    if user is None:
        user = User(username=username, role_name="viewer")
        await user.insert()
    return user


async def get_user_permissions(username: str) -> List[str]:
    user = await User.find_one(User.username == username)
    if user is None:
        return []
    role_permissions_map = await get_role_permissions_map()
    return compute_permissions(
        user.role_name,
        user.extra_permissions,
        user.denied_permissions,
        role_permissions_map,
    )
