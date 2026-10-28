from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import HabitCheckin, HabitCreate, HabitOut, HabitSkip, HabitUpdate
from app.services.task import habit_service

router = APIRouter()


def _habit_out(habit, today_checked=False, streak=0, week_bitmap=None, today_count=0, today_skipped=False, total_days=0) -> HabitOut:
    return HabitOut(
        id=str(habit.id),
        name=habit.name,
        color=habit.color,
        icon=getattr(habit, "icon", None) or "smile",
        freq=habit.freq,
        target_per_day=habit.target_per_day,
        target_per_week=habit.target_per_week,
        start_date=habit.start_date,
        group=habit.group,
        checkin_style=getattr(habit, "checkin_style", "check") or "check",
        is_archived=habit.is_archived,
        goal_type=getattr(habit, "goal_type", "amount") or "amount",
        checkin_mode=getattr(habit, "checkin_mode", "auto") or "auto",
        reminders=getattr(habit, "reminders", None) or [],
        auto_log=getattr(habit, "auto_log", True),
        motto=getattr(habit, "motto", "") or "",
        today_checked=today_checked,
        today_skipped=today_skipped,
        today_count=today_count,
        streak=streak,
        total_days=total_days,
        week_bitmap=week_bitmap or [],
        created_at=habit.created_at,
    )


@router.get("")
async def list_habits(
    tz_offset_minutes: int = 0,
    date: Optional[str] = None,
    current_user: User = Depends(require_perm("task:view")),
):
    """date（YYYY-MM-DD）缺省今天：返回各习惯该日达标状态（周环条/列表用）。"""
    rows = await habit_service.list_habits(current_user.username, tz_offset_minutes, date)
    return {"items": [_habit_out(h, checked, streak, bitmap, cnt, skipped, total) for h, checked, streak, bitmap, cnt, skipped, total in rows]}


@router.get("/week")
async def week_overview(
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:view")),
):
    """本周概览（周一~周日每天达标习惯数/总数），左上圆环条用。"""
    return {"days": await habit_service.week_overview(current_user.username, tz_offset_minutes)}


@router.get("/{habit_id}/stats")
async def habit_stats(
    habit_id: str,
    month: Optional[str] = None,
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:view")),
):
    """详情四卡 + 月历打卡表 + 月度概览。"""
    return await habit_service.habit_stats(habit_id, current_user.username, month, tz_offset_minutes)


@router.post("", response_model=HabitOut)
async def create_habit(
    data: HabitCreate,
    current_user: User = Depends(require_perm("task:create")),
):
    habit = await habit_service.create_habit(
        data.name,
        data.color,
        current_user.username,
        freq=data.freq,
        target_per_day=data.target_per_day,
        target_per_week=data.target_per_week,
        start_date=data.start_date,
        group=data.group,
        icon=data.icon,
        goal_type=data.goal_type,
        checkin_mode=data.checkin_mode,
        reminders=data.reminders,
        auto_log=data.auto_log,
        motto=data.motto,
    )
    return _habit_out(habit)


@router.patch("/{habit_id}", response_model=HabitOut)
async def update_habit(
    habit_id: str,
    data: HabitUpdate,
    current_user: User = Depends(require_perm("task:edit")),
):
    habit = await habit_service.update_habit(
        habit_id, data.model_dump(exclude_unset=True), current_user.username
    )
    return _habit_out(habit)


@router.delete("/{habit_id}")
async def delete_habit(
    habit_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await habit_service.delete_habit(habit_id, current_user.username)
    return {"ok": True}


@router.post("/{habit_id}/checkin")
async def checkin(
    habit_id: str,
    data: HabitCheckin,
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:run")),
):
    log = await habit_service.checkin(
        habit_id, current_user.username, data.date, data.note, tz_offset_minutes, mood=data.mood, amount=data.amount, meta_only=data.meta_only
    )
    return {"ok": True, "date": log.date, "count": log.checkin_count}


@router.post("/{habit_id}/skip")
async def skip_habit(
    habit_id: str,
    data: Optional[HabitSkip] = None,
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:run")),
):
    """跳过当日打卡：不算打卡也不打断 streak；当日已达标返回 400。"""
    log = await habit_service.skip(
        habit_id, current_user.username, (data or HabitSkip()).date, tz_offset_minutes
    )
    return {"ok": True, "date": log.date, "skipped": True}


@router.delete("/{habit_id}/checkin")
async def uncheckin(
    habit_id: str,
    date: Optional[str] = None,
    tz_offset_minutes: int = 0,
    current_user: User = Depends(require_perm("task:run")),
):
    await habit_service.uncheckin(habit_id, current_user.username, date, tz_offset_minutes)
    return {"ok": True}


@router.get("/{habit_id}/logs")
async def list_logs(
    habit_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    current_user: User = Depends(require_perm("task:view")),
):
    logs = await habit_service.list_logs(habit_id, current_user.username, start, end)
    return {
        "items": [
            {"id": str(log.id), "date": log.date, "count": log.checkin_count, "skipped": log.skipped, "mood": log.mood, "note": log.note, "created_at": log.created_at}
            for log in logs
        ]
    }
