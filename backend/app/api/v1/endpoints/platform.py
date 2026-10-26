from typing import List

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_current_user, require_perm
from app.core.exceptions import bad_request, not_found, forbidden
from app.models.user import SsoPlatformConfig, PermissionKeyItem, User
from app.schemas.auth import PermissionKeyCreate

router = APIRouter()


async def _get_config() -> SsoPlatformConfig:
    config = await SsoPlatformConfig.find_one()
    if config is None:
        config = SsoPlatformConfig(permission_keys=[])
        await config.insert()
    return config


@router.get("/permissions")
async def list_permissions(current_user: User = Depends(get_current_user)):
    config = await _get_config()
    return {"items": [item.model_dump() for item in config.permission_keys]}


@router.post("/permissions")
async def create_permission(
    data: PermissionKeyCreate,
    current_user: User = Depends(require_perm("sys:manage")),
):
    config = await _get_config()
    existing = next((item for item in config.permission_keys if item.key == data.key), None)
    if existing is not None:
        raise bad_request("permission_exists", "权限 key 已存在")
    config.permission_keys.append(
        PermissionKeyItem(key=data.key, app_id=data.app_id, builtin=data.builtin)
    )
    await config.save()
    return {"item": data.model_dump()}


@router.delete("/permissions/{key:path}")
async def delete_permission(
    key: str = Path(..., description="权限 key"),
    current_user: User = Depends(require_perm("sys:manage")),
):
    config = await _get_config()
    item = next((item for item in config.permission_keys if item.key == key), None)
    if item is None:
        raise not_found("permission_not_found", "权限 key 不存在")
    if item.builtin:
        raise forbidden("内置权限 key 不可删除")
    config.permission_keys = [i for i in config.permission_keys if i.key != key]
    await config.save()
    return {"message": "已删除"}
