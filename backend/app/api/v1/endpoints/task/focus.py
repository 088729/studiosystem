from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.core.exceptions import bad_request
from app.models.user import User
from app.schemas.task import (
    FocusRecordCreate,
    FocusRecordsDelete,
    FocusSessionOut,
    FocusStart,
    FocusUpdate,
)
from app.services.task import focus_service

router = APIRouter()


def _session_out(session) -> FocusSessionOut:
    return FocusSessionOut(
        id=str(session.id),
        task_id=session.task_id,
        preset_id=session.preset_id,
        owner=session.owner,
        planned_minutes=session.planned_minutes,
        actual_seconds=session.actual_seconds,
        status=session.status,
        paused_at=session.paused_at,
        paused_seconds=session.paused_seconds,
        note=session.note,
        started_at=session.started_at,
        ended_at=session.ended_at,
        habit_id=session.habit_id,
    )


@router.post("", response_model=FocusSessionOut)
async def start_session(
    data: FocusStart,
    current_user: User = Depends(require_perm("task:run")),
):
    session = await focus_service.start_session(
        current_user.username, data.task_id, data.planned_minutes, data.preset_id, data.habit_id
    )
    return _session_out(session)


@router.post("/{session_id}/finish", response_model=FocusSessionOut)
async def finish_session(
    session_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    session = await focus_service.finish_session(session_id, current_user.username)
    return _session_out(session)


@router.post("/{session_id}/abandon", response_model=FocusSessionOut)
async def abandon_session(
    session_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    session = await focus_service.abandon_session(session_id, current_user.username)
    return _session_out(session)


@router.post("/{session_id}/pause", response_model=FocusSessionOut)
async def pause_session(
    session_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    session = await focus_service.pause_session(session_id, current_user.username)
    return _session_out(session)


@router.post("/{session_id}/resume", response_model=FocusSessionOut)
async def resume_session(
    session_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    session = await focus_service.resume_session(session_id, current_user.username)
    return _session_out(session)


@router.patch("/{session_id}", response_model=FocusSessionOut)
async def update_session(
    session_id: str,
    data: FocusUpdate,
    current_user: User = Depends(require_perm("task:run")),
):
    """专注中调计划时长（±调时）；结束后改实际时长 / 专注笔记。"""
    session = await focus_service.update_session(
        session_id,
        current_user.username,
        planned_minutes=data.planned_minutes,
        actual_seconds=data.actual_seconds,
        note=data.note,
    )
    return _session_out(session)


@router.post("/records", response_model=FocusSessionOut)
async def add_record(
    data: FocusRecordCreate,
    current_user: User = Depends(require_perm("task:run")),
):
    """补记一条已完成专注记录。"""
    session = await focus_service.add_record(
        current_user.username,
        data.task_id,
        data.planned_minutes,
        data.actual_seconds,
        data.started_at,
        data.note,
        data.preset_id,
    )
    return _session_out(session)


@router.get("")
async def list_sessions(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    running_only: bool = False,
    current_user: User = Depends(require_perm("task:view")),
):
    if running_only:
        session = await focus_service.get_running(current_user.username)
        return {"items": [_session_out(session)] if session else []}
    sessions = await focus_service.list_sessions(current_user.username, start, end)
    return {"items": [_session_out(s) for s in sessions]}


@router.get("/stats")
async def focus_stats(
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:view")),
):
    return await focus_service.stats(current_user.username, tz_offset_minutes)


@router.get("/stats/detail")
async def focus_stats_detail(
    kind: str,
    period: str = "week",
    by: str = "task",
    date: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[str] = None,
    week_start: Optional[str] = None,
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:view")),
):
    """第三期专注统计聚合：trend（周/月趋势）/ hours（24h 分布）/ heatmap（年度）/ timeline（周矩阵）/ breakdown（占比排行）。"""
    owner = current_user.username
    if kind == "trend":
        return await focus_service.stats_trend(owner, period, date, tz_offset_minutes)
    if kind == "hours":
        return await focus_service.stats_hours(owner, month, tz_offset_minutes)
    if kind == "heatmap":
        return await focus_service.stats_heatmap(owner, year, tz_offset_minutes)
    if kind == "timeline":
        return await focus_service.stats_timeline(owner, week_start, tz_offset_minutes)
    if kind == "breakdown":
        return await focus_service.stats_breakdown(owner, by, period, date, tz_offset_minutes)
    raise bad_request("invalid_kind", "kind 仅支持 trend/hours/heatmap/timeline/breakdown")


@router.delete("/records")
async def delete_records(
    data: FocusRecordsDelete,
    current_user: User = Depends(require_perm("task:run")),
):
    """删除专注记录（批量 ids 或 all 清空；running 不可删）。"""
    n = await focus_service.delete_records(
        current_user.username, ids=data.ids, all_records=data.all
    )
    return {"deleted": n}
