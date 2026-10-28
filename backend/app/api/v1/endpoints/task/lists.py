from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import ListGroupCreate, ListGroupMove, ListGroupRename, TaskListCreate, TaskListOut, TaskListUpdate
from app.services.task import list_service, share_service

router = APIRouter()


def _list_out(task_list, current_user: str = "") -> TaskListOut:
    return TaskListOut(
        id=str(task_list.id),
        name=task_list.name,
        owner=task_list.owner,
        members=task_list.members or [],
        is_shared=bool(current_user) and task_list.owner != current_user,
        color=task_list.color,
        icon=getattr(task_list, "icon", None),
        group=task_list.group,
        board_groups=task_list.board_groups or [],
        kind=task_list.kind,
        sort_order=task_list.sort_order,
        is_archived=task_list.is_archived,
        created_at=task_list.created_at,
    )


@router.get("")
async def list_lists(current_user: User = Depends(require_perm("task:view"))):
    own = await list_service.list_lists(current_user.username)
    shared = await share_service.list_shared_lists(current_user.username)
    return {"items": [_list_out(item, current_user.username) for item in own + shared]}


@router.post("", response_model=TaskListOut)
async def create_list(
    data: TaskListCreate,
    current_user: User = Depends(require_perm("task:create")),
):
    task_list = await list_service.create_list(
        data.name, data.color, current_user.username, data.group, data.icon, data.kind
    )
    return _list_out(task_list)


@router.patch("/{list_id}", response_model=TaskListOut)
async def update_list(
    list_id: str,
    data: TaskListUpdate,
    current_user: User = Depends(require_perm("task:manage")),
):
    task_list = await list_service.update_list(
        list_id, data.model_dump(exclude_unset=True), current_user.username
    )
    return _list_out(task_list)


@router.delete("/{list_id}")
async def delete_list(
    list_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await list_service.delete_list(list_id, current_user.username)
    return {"ok": True}


# ---------- 看板分组 ----------


@router.post("/groups/move")
async def move_group(
    data: ListGroupMove,
    current_user: User = Depends(require_perm("task:manage")),
):
    # 分组「移动到」另一清单/收集箱（from/to 为 null 表示收集箱）；前端移动后自行重拉清单/任务
    await list_service.move_group(current_user.username, data.name, data.from_list_id, data.to_list_id)
    return {"ok": True}


@router.post("/{list_id}/groups", response_model=TaskListOut)
async def add_group(
    list_id: str,
    data: ListGroupCreate,
    current_user: User = Depends(require_perm("task:manage")),
):
    task_list = await list_service.add_group(list_id, data.name, current_user.username, data.index)
    return _list_out(task_list)


@router.patch("/{list_id}/groups", response_model=TaskListOut)
async def rename_group(
    list_id: str,
    data: ListGroupRename,
    current_user: User = Depends(require_perm("task:manage")),
):
    task_list = await list_service.rename_group(
        list_id, data.from_name, data.to_name, current_user.username
    )
    return _list_out(task_list)


@router.delete("/{list_id}/groups/{name}", response_model=TaskListOut)
async def delete_group(
    list_id: str,
    name: str,
    current_user: User = Depends(require_perm("task:manage")),
):
    task_list = await list_service.delete_group(list_id, name, current_user.username)
    return _list_out(task_list)
