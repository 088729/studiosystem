from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel

from app.api.deps import require_perm
from app.core.exceptions import bad_request
from app.models.user import User
from app.schemas.task import (
    AttachmentIn,
    TaskBatch,
    TaskComplete,
    TaskCreate,
    TaskDetailOut,
    TaskMove,
    TaskOut,
    TaskSort,
    TaskUpdate,
)
from app.services.task import task_service
from app.services.task.recurrence import next_due

router = APIRouter()


def _task_out(task, counts: Optional[dict] = None) -> TaskOut:
    total, done = (counts or {}).get(str(task.id), (0, 0))
    next_due_at = None
    occ = 0
    if task.recurrence and task.due_at:
        d = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        next_due_at = next_due(task.recurrence, d)
        occ = task.recurrence.occurrences_completed
    return TaskOut(
        id=str(task.id),
        title=task.title,
        note=task.note,
        list_id=task.list_id,
        group=task.group,
        parent_id=task.parent_id,
        owner=task.owner,
        assignee=task.assignee,
        status=task.status,
        completed_at=task.completed_at,
        priority=task.priority,
        tags=task.tags,
        due_at=task.due_at,
        all_day=task.all_day,
        start_at=task.start_at,
        duration_minutes=task.duration_minutes,
        reminders=task.reminders,
        persistent_reminder=task.persistent_reminder,
        attachments=task.attachments or [],
        recurrence=task.recurrence,
        next_due=next_due_at,
        occurrences_completed=occ,
        case_map_id=task.case_map_id,
        case_node_id=task.case_node_id,
        is_pinned=task.is_pinned,
        is_note=task.is_note,
        sort_order=task.sort_order,
        subtask_total=total,
        subtask_done=done,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _task_out_with_counts(task) -> TaskOut:
    """带子任务进度计数输出（B5：单任务接口也需返回 subtask_total/done）。"""
    counts = await task_service.get_subtask_counts([str(task.id)])
    return _task_out(task, counts)


@router.get("")
async def list_tasks(
    list_id: Optional[str] = None,
    smart: Optional[str] = None,
    filter_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    tz_offset_minutes: int = Query(0, ge=-840, le=840),
    limit: int = 200,
    offset: int = 0,
    current_user: User = Depends(require_perm("task:view")),
):
    tasks = await task_service.list_tasks(
        owner=current_user.username,
        list_id=list_id,
        smart=smart,
        filter_id=filter_id,
        status=status,
        priority=priority,
        tag=tag,
        q=q,
        tz_offset_minutes=tz_offset_minutes,
        limit=limit,
        offset=offset,
    )
    counts = await task_service.get_subtask_counts([str(t.id) for t in tasks])
    return {"items": [_task_out(t, counts) for t in tasks]}


@router.post("", response_model=TaskOut)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(require_perm("task:create")),
):
    task = await task_service.create_task(current_user.username, data)
    return _task_out(task)


@router.post("/batch")
async def batch_tasks(
    data: TaskBatch,
    current_user: User = Depends(require_perm("task:edit")),
):
    """批量操作：complete/delete/move/priority/due，逐条校验 owner 或共享写权限。"""
    return await task_service.batch_task(current_user.username, data.ids, data.action, data.payload)


@router.get("/{task_id}", response_model=TaskDetailOut)
async def get_task(
    task_id: str,
    current_user: User = Depends(require_perm("task:view")),
):
    task = await task_service.get_task_or_404(task_id, current_user.username)
    subtasks = await task_service.get_subtasks(task_id)
    case_map_title, case_node_text = await task_service.get_case_ref(task)
    detail = _task_out(
        task,
        {str(task.id): (len(subtasks), sum(1 for s in subtasks if s.status == "done"))},
    )
    return TaskDetailOut(
        **detail.model_dump(),
        subtasks=[_task_out(s) for s in subtasks],
        case_map_title=case_map_title,
        case_node_text=case_node_text,
    )


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user: User = Depends(require_perm("task:edit")),
):
    task = await task_service.update_task(
        task_id, data.model_dump(exclude_unset=True), current_user.username
    )
    return await _task_out_with_counts(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await task_service.soft_delete_task(task_id, current_user.username)
    return {"ok": True}


@router.post("/{task_id}/attachments", response_model=TaskOut)
async def add_attachment(
    task_id: str,
    data: AttachmentIn,
    current_user: User = Depends(require_perm("task:edit")),
):
    """登记附件引用（文件本体经 resourceplatform 上传，resource_id 含 /，故删除接口用 :path）。"""
    task = await task_service.add_attachment(task_id, current_user.username, data)
    return await _task_out_with_counts(task)


@router.post("/{task_id}/attachments/upload", response_model=TaskOut)
async def upload_attachment(
    task_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("task:edit")),
):
    """上传附件（转发 resourceplatform 并登记引用，对齐主流待办应用「/」菜单附件项）。"""
    if file.size and file.size > task_service.MAX_ATTACHMENT_SIZE:
        raise bad_request("attachment_too_large", "附件大小不能超过 5MB")
    file_bytes = await file.read()
    task = await task_service.upload_attachment(
        task_id, current_user.username, file.filename or "unnamed", file.content_type, file_bytes
    )
    return await _task_out_with_counts(task)


@router.delete("/{task_id}/attachments/{resource_id:path}")
async def remove_attachment(
    task_id: str,
    resource_id: str,
    current_user: User = Depends(require_perm("task:edit")),
):
    await task_service.remove_attachment(task_id, resource_id, current_user.username)
    return {"ok": True}


@router.post("/{task_id}/restore", response_model=TaskOut)
async def restore_task(
    task_id: str,
    current_user: User = Depends(require_perm("task:edit")),
):
    task = await task_service.restore_task(task_id, current_user.username)
    return await _task_out_with_counts(task)


@router.delete("/{task_id}/purge")
async def purge_task(
    task_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await task_service.purge_task(task_id, current_user.username)
    return {"ok": True}


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: str,
    data: TaskComplete,
    current_user: User = Depends(require_perm("task:run")),
):
    task = await task_service.complete_task(task_id, data.done, current_user.username)
    return await _task_out_with_counts(task)


@router.post("/{task_id}/skip", response_model=TaskOut)
async def skip_task(
    task_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    task = await task_service.skip_task(task_id, current_user.username)
    return await _task_out_with_counts(task)


class AckReminders(BaseModel):
    snooze_minutes: Optional[int] = None


@router.post("/{task_id}/reminders/ack")
async def ack_reminders(
    task_id: str,
    data: Optional[AckReminders] = None,
    current_user: User = Depends(require_perm("task:view")),
):
    await task_service.ack_reminders(task_id, current_user.username, (data or AckReminders()).snooze_minutes)
    return {"ok": True}


@router.patch("/{task_id}/move", response_model=TaskOut)
async def move_task(
    task_id: str,
    data: TaskMove,
    current_user: User = Depends(require_perm("task:edit")),
):
    task = await task_service.move_task(task_id, data.list_id, current_user.username)
    return await _task_out_with_counts(task)


@router.patch("/{task_id}/sort", response_model=TaskOut)
async def sort_task(
    task_id: str,
    data: TaskSort,
    current_user: User = Depends(require_perm("task:edit")),
):
    task = await task_service.sort_task(
        task_id, current_user.username, data.sort_order, data.before_task_id, data.after_task_id
    )
    return await _task_out_with_counts(task)
