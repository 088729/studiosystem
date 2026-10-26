from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import (
    TaskFilterCreate,
    TaskFilterOut,
    TaskFilterResponse,
    TaskFilterUpdate,
)
from app.services.task import filter_service, task_service

router = APIRouter()


def _filter_out(f, count: int = 0) -> TaskFilterOut:
    return TaskFilterOut(
        id=str(f.id),
        name=f.name,
        lists=f.lists,
        tags=f.tags,
        priorities=f.priorities,
        due_range=f.due_range,
        status=f.status,
        keyword=f.keyword,
        sort_order=f.sort_order,
        count=count,
    )


@router.get("", response_model=TaskFilterResponse)
async def list_filters(
    tz_offset_minutes: int = 480,
    current_user: User = Depends(require_perm("task:view")),
):
    items = await filter_service.list_filters(current_user.username)
    bounds = task_service._day_bounds_utc(tz_offset_minutes)  # 复用任务列表的日界口径
    return {
        "items": [
            _filter_out(f, await filter_service.count_filter_tasks(f, current_user.username, bounds))
            for f in items
        ]
    }


@router.post("", response_model=TaskFilterOut)
async def create_filter(
    data: TaskFilterCreate,
    current_user: User = Depends(require_perm("task:create")),
):
    f = await filter_service.create_filter(current_user.username, data)
    return _filter_out(f)


@router.patch("/{filter_id}", response_model=TaskFilterOut)
async def update_filter(
    filter_id: str,
    data: TaskFilterUpdate,
    current_user: User = Depends(require_perm("task:edit")),
):
    f = await filter_service.update_filter(
        filter_id, current_user.username, data.model_dump(exclude_unset=True)
    )
    return _filter_out(f)


@router.delete("/{filter_id}")
async def delete_filter(
    filter_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await filter_service.delete_filter(filter_id, current_user.username)
    return {"ok": True}
