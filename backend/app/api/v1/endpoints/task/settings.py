from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import ListGroupCreate, ListGroupRename, TaskSettingsOut, TaskSettingsUpdate
from app.services.task import settings_service

router = APIRouter()


@router.get("", response_model=TaskSettingsOut)
async def get_settings(current_user: User = Depends(require_perm("task:view"))):
    """当前用户的任务默认值（无记录返回默认值）。"""
    return await settings_service.get_settings(current_user.username)


@router.put("", response_model=TaskSettingsOut)
async def save_settings(
    data: TaskSettingsUpdate,
    current_user: User = Depends(require_perm("task:edit")),
):
    """整体 upsert 任务默认值。"""
    return await settings_service.save_settings(
        current_user.username, data.model_dump(exclude_unset=True)
    )


# ---------- 收集箱自定义分组（对齐主流待办应用：收集箱支持分组管理） ----------


@router.post("/inbox-groups")
async def add_inbox_group(
    data: ListGroupCreate,
    current_user: User = Depends(require_perm("task:manage")),
):
    s = await settings_service.add_inbox_group(current_user.username, data.name, data.index)
    return {"board_groups": s.inbox_board_groups or []}


@router.patch("/inbox-groups")
async def rename_inbox_group(
    data: ListGroupRename,
    current_user: User = Depends(require_perm("task:manage")),
):
    s = await settings_service.rename_inbox_group(current_user.username, data.from_name, data.to_name)
    return {"board_groups": s.inbox_board_groups or []}


@router.delete("/inbox-groups/{name}")
async def delete_inbox_group(
    name: str,
    current_user: User = Depends(require_perm("task:manage")),
):
    s = await settings_service.delete_inbox_group(current_user.username, name)
    return {"board_groups": s.inbox_board_groups or []}
