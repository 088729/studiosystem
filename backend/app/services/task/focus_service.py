"""番茄钟专注会话服务（模块级函数，对齐 task_service 风格）。"""
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.task.focus_preset import FocusPreset
from app.models.task.focus_session import FocusSession
from app.models.task.task import Task
from app.services.case.folder_service import is_valid_oid
from app.services.task import share_service


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _effective_elapsed_seconds(session: FocusSession, now: datetime) -> int:
    """有效专注秒 = 经过时间 - 已恢复暂停 - 进行中的暂停。"""
    elapsed = (_utc(now) - _utc(session.started_at)).total_seconds()
    paused = session.paused_seconds
    if session.paused_at is not None:
        paused += (_utc(now) - _utc(session.paused_at)).total_seconds()
    return max(0, int(elapsed - paused))


async def _get_session_or_404(session_id: str, owner: str) -> FocusSession:
    if not is_valid_oid(session_id):
        raise not_found("session_not_found", "专注会话不存在")
    session = await FocusSession.get(ObjectId(session_id))
    if session is None or session.owner != owner:
        raise not_found("session_not_found", "专注会话不存在")
    return session


async def start_session(
    owner: str,
    task_id: Optional[str],
    planned_minutes: int,
    preset_id: Optional[str] = None,
    habit_id: Optional[str] = None,
) -> FocusSession:
    if planned_minutes < 0 or planned_minutes > 180:
        raise bad_request("invalid_duration", "计划时长须在 0~180 分钟之间（0 = 不限时正计时）")
    running = await FocusSession.find(
        FocusSession.owner == owner, FocusSession.status == "running"
    ).to_list()
    if running:
        raise bad_request("session_running", "已有进行中的专注会话，请先完成或放弃")
    if preset_id:
        preset = await FocusPreset.get(ObjectId(preset_id))
        if preset is None or preset.owner != owner:
            raise not_found("preset_not_found", "常用专注不存在")
        if not task_id:
            task_id = preset.task_id  # 预设未显式传任务时沿用其关联任务
        if not habit_id:
            habit_id = preset.habit_id  # 预设未显式传习惯时沿用其关联习惯
    if task_id:
        task = await share_service.get_task_or_none(task_id)
        if task is None or task.is_deleted or not await share_service.can_access_task(task, owner):
            raise not_found("task_not_found", "关联任务不存在")
    session = FocusSession(
        task_id=task_id, owner=owner, planned_minutes=planned_minutes, preset_id=preset_id, habit_id=habit_id
    )
    await session.insert()
    return session


async def _close_session(session: FocusSession, status: str) -> FocusSession:
    if session.status != "running":
        return session  # 幂等
    now = datetime.now(timezone.utc)
    session.status = status
    session.ended_at = now
    session.actual_seconds = _effective_elapsed_seconds(session, now)
    if session.paused_at is not None:
        # 暂停中直接结束：把进行中的暂停累计进去，避免后续再被重复扣除
        session.paused_seconds += int((_utc(now) - _utc(session.paused_at)).total_seconds())
        session.paused_at = None
    await session.save()
    return session


async def pause_session(session_id: str, owner: str) -> FocusSession:
    """暂停（幂等）：记录暂停开始时刻，实际秒数在恢复/结束时补扣。"""
    session = await _get_session_or_404(session_id, owner)
    if session.status != "running":
        raise bad_request("session_not_running", "专注会话已结束")
    if session.paused_at is None:
        session.paused_at = datetime.now(timezone.utc)
        await session.save()
    return session


async def resume_session(session_id: str, owner: str) -> FocusSession:
    """恢复（幂等）：累计已暂停时长，清空暂停起点。"""
    session = await _get_session_or_404(session_id, owner)
    if session.paused_at is not None:
        now = datetime.now(timezone.utc)
        session.paused_seconds += int((_utc(now) - _utc(session.paused_at)).total_seconds())
        session.paused_at = None
        await session.save()
    return session


async def update_session(
    session_id: str,
    owner: str,
    planned_minutes: Optional[int] = None,
    actual_seconds: Optional[int] = None,
    note: Optional[str] = None,
) -> FocusSession:
    """专注中调计划时长（±调时）；结束后改实际时长/笔记。"""
    session = await _get_session_or_404(session_id, owner)
    if planned_minutes is not None:
        if session.status != "running":
            raise bad_request("session_not_running", "只有进行中的专注可以调整时长")
        session.planned_minutes = planned_minutes
    if actual_seconds is not None:
        if session.status == "running":
            raise bad_request("session_running", "进行中的专注请先结束再编辑时长")
        session.actual_seconds = actual_seconds
    if note is not None:
        session.note = note
    await session.save()
    return session


async def add_record(
    owner: str,
    task_id: Optional[str],
    planned_minutes: int,
    actual_seconds: int,
    started_at: datetime,
    note: str = "",
    preset_id: Optional[str] = None,
) -> FocusSession:
    """补记一条已完成专注记录。"""
    if task_id:
        task = await share_service.get_task_or_none(task_id)
        if task is None or task.is_deleted or not await share_service.can_access_task(task, owner):
            raise not_found("task_not_found", "关联任务不存在")
    if preset_id:
        preset = await FocusPreset.get(ObjectId(preset_id))
        if preset is None or preset.owner != owner:
            raise not_found("preset_not_found", "常用专注不存在")
    started = _utc(started_at)
    session = FocusSession(
        task_id=task_id,
        owner=owner,
        planned_minutes=planned_minutes,
        actual_seconds=actual_seconds,
        status="completed",
        note=note,
        preset_id=preset_id,
        started_at=started,
        ended_at=started + timedelta(seconds=actual_seconds),
    )
    await session.insert()
    return session


async def finish_session(session_id: str, owner: str) -> FocusSession:
    session = await _get_session_or_404(session_id, owner)
    closed = await _close_session(session, "completed")
    # 关联习惯的专注：完成时自动打卡（失败静默，不阻断结束流程）
    if closed.habit_id:
        try:
            from app.services.task.habit_service import checkin
            await checkin(closed.habit_id, owner, None, "专注自动打卡")
        except Exception:
            pass
    return closed


async def abandon_session(session_id: str, owner: str) -> FocusSession:
    session = await _get_session_or_404(session_id, owner)
    return await _close_session(session, "abandoned")


async def get_running(owner: str) -> Optional[FocusSession]:
    return await FocusSession.find_one(
        FocusSession.owner == owner, FocusSession.status == "running"
    )


async def list_sessions(
    owner: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
) -> List[FocusSession]:
    conditions = [FocusSession.owner == owner]
    if start:
        conditions.append(FocusSession.started_at >= start)
    if end:
        conditions.append(FocusSession.started_at < end)
    return (
        await FocusSession.find(*conditions)
        .sort("-started_at")
        .limit(limit)
        .to_list()
    )


async def stats(owner: str, tz_offset_minutes: int = 0) -> dict:
    """今日完成数 / 今日专注分钟 / 历史完成总数。今日边界按客户端时区。"""
    local_now = datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)
    local_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = local_today - timedelta(minutes=tz_offset_minutes)

    base = [FocusSession.owner == owner, FocusSession.status == "completed"]
    total_completed = await FocusSession.find(*base).count()
    today_sessions = await FocusSession.find(*base, FocusSession.started_at >= today_start).to_list()
    today_seconds = sum(s.actual_seconds for s in today_sessions)
    agg = (
        await FocusSession.find(*base)
        .aggregate([{"$group": {"_id": None, "s": {"$sum": "$actual_seconds"}}}])
        .to_list(1)
    )
    total_minutes = (agg[0]["s"] if agg else 0) // 60
    return {
        "today_completed": len(today_sessions),
        "today_minutes": today_seconds // 60,
        "total_completed": total_completed,
        "total_minutes": total_minutes,
    }


# ---------- 第三期：专注统计聚合 ----------


def _parse_day(date_str: Optional[str], tz_offset_minutes: int) -> date:
    if date_str:
        return date.fromisoformat(date_str)
    return (datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)).date()


def _day_range(start_day: date, days: int, tz_offset_minutes: int):
    """本地日期区间 → UTC 时间范围。"""
    start_utc = datetime.combine(start_day, datetime.min.time()) - timedelta(minutes=tz_offset_minutes)
    return start_utc, start_utc + timedelta(days=days)


async def _completed_in_range(owner: str, start_utc: datetime, end_utc: datetime) -> List[FocusSession]:
    return await FocusSession.find(
        FocusSession.owner == owner,
        FocusSession.status == "completed",
        FocusSession.started_at >= start_utc,
        FocusSession.started_at < end_utc,
    ).to_list()


async def stats_trend(
    owner: str, period: str, date_str: Optional[str], tz_offset_minutes: int
) -> dict:
    """专注趋势：周（7 天）或月（自然月）按天分钟序列 + 每日平均。"""
    anchor = _parse_day(date_str, tz_offset_minutes)
    if period == "month":
        start_day = anchor.replace(day=1)
        import calendar

        days_n = calendar.monthrange(anchor.year, anchor.month)[1]
        labels = [str(i + 1) for i in range(days_n)]
    else:
        period = "week"
        start_day = anchor - timedelta(days=anchor.weekday())
        days_n = 7
        labels = list("一二三四五六日")
    start_utc, end_utc = _day_range(start_day, days_n, tz_offset_minutes)
    sessions = await _completed_in_range(owner, start_utc, end_utc)
    minutes = [0] * days_n
    for s in sessions:
        local_day = (_utc(s.started_at) + timedelta(minutes=tz_offset_minutes)).date()
        idx = (local_day - start_day).days
        if 0 <= idx < days_n:
            minutes[idx] += s.actual_seconds // 60
    total = sum(minutes)
    now_day = _parse_day(None, tz_offset_minutes)
    is_current = start_day <= now_day < start_day + timedelta(days=days_n)
    if period == "week":
        range_label = "本周" if is_current else f"{start_day.month}月{start_day.day}日 - {(start_day + timedelta(days=6)).day}日"
    else:
        range_label = f"{anchor.month}月" if is_current else f"{anchor.year}年{anchor.month}月"
    return {
        "period": period,
        "labels": labels,
        "minutes": minutes,
        "total_minutes": total,
        "avg_minutes": total // days_n,
        "range_label": range_label,
        "is_current": is_current,
        "anchor": start_day.isoformat(),
    }


async def stats_hours(owner: str, month_str: Optional[str], tz_offset_minutes: int) -> dict:
    """最佳专注时间：某月 24 小时分钟分布。"""
    if month_str:
        year, month = (int(x) for x in month_str.split("-"))
    else:
        today = _parse_day(None, tz_offset_minutes)
        year, month = today.year, today.month
    import calendar

    days_n = calendar.monthrange(year, month)[1]
    start_utc, end_utc = _day_range(date(year, month, 1), days_n, tz_offset_minutes)
    sessions = await _completed_in_range(owner, start_utc, end_utc)
    hours = [0] * 24
    for s in sessions:
        local = _utc(s.started_at) + timedelta(minutes=tz_offset_minutes)
        hours[local.hour] += s.actual_seconds // 60
    return {
        "month": f"{month}月",
        "year_month": f"{year}-{month:02d}",
        "hours": hours,
        "max_minutes": max(hours) if hours else 0,
    }


async def stats_heatmap(owner: str, year_str: Optional[str], tz_offset_minutes: int) -> dict:
    """年度热力图：当年每天分钟数（稀疏 map）。"""
    if year_str:
        year = int(year_str)
    else:
        year = _parse_day(None, tz_offset_minutes).year
    start_utc, end_utc = _day_range(date(year, 1, 1), 366 if _is_leap(year) else 365, tz_offset_minutes)
    sessions = await _completed_in_range(owner, start_utc, end_utc)
    days: dict = {}
    for s in sessions:
        local_day = (_utc(s.started_at) + timedelta(minutes=tz_offset_minutes)).date()
        key = local_day.isoformat()
        days[key] = days.get(key, 0) + s.actual_seconds // 60
    return {"year": year, "days": days}


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


async def stats_timeline(
    owner: str, week_start_str: Optional[str], tz_offset_minutes: int
) -> dict:
    """专注时间线：一周 7 天 × 24 小时分钟矩阵（前端按 4h 行聚合渲染）。"""
    if week_start_str:
        start_day = date.fromisoformat(week_start_str)
    else:
        today = _parse_day(None, tz_offset_minutes)
        start_day = today - timedelta(days=today.weekday())
    start_utc, end_utc = _day_range(start_day, 7, tz_offset_minutes)
    sessions = await _completed_in_range(owner, start_utc, end_utc)
    cells = [[0] * 24 for _ in range(7)]
    for s in sessions:
        local = _utc(s.started_at) + timedelta(minutes=tz_offset_minutes)
        day_idx = (local.date() - start_day).days
        if 0 <= day_idx < 7:
            cells[day_idx][local.hour] += s.actual_seconds // 60
    now_day = _parse_day(None, tz_offset_minutes)
    this_monday = now_day - timedelta(days=now_day.weekday())
    return {
        "week_label": "本周" if start_day == this_monday else f"{start_day.month}月{start_day.day}日 - {(start_day + timedelta(days=6)).day}日",
        "cells": cells,
        "week_start": start_day.isoformat(),
    }


async def stats_breakdown(
    owner: str, by: str, period: str, date_str: Optional[str], tz_offset_minutes: int
) -> dict:
    """专注详情占比/排行：按任务或按清单聚合某 天/周/月 的分钟。"""
    anchor = _parse_day(date_str, tz_offset_minutes)
    if period == "month":
        start_day = anchor.replace(day=1)
        import calendar

        days_n = calendar.monthrange(anchor.year, anchor.month)[1]
    elif period == "day":
        start_day, days_n = anchor, 1
    else:
        period = "week"
        start_day = anchor - timedelta(days=anchor.weekday())
        days_n = 7
    start_utc, end_utc = _day_range(start_day, days_n, tz_offset_minutes)
    sessions = await _completed_in_range(owner, start_utc, end_utc)

    # 按任务聚合
    by_task: dict = {}
    for s in sessions:
        by_task[s.task_id] = by_task.get(s.task_id, 0) + s.actual_seconds // 60
    task_names = await _resolve_task_names(list(by_task.keys()))
    if by == "list":
        # 任务 → 清单再聚合
        task_lists = await _resolve_task_lists(list(by_task.keys()))
        by_list: dict = {}
        for tid, minutes in by_task.items():
            key = task_lists.get(tid) or "none"
            by_list[key] = by_list.get(key, 0) + minutes
        items = [
            {"key": k, "name": await _list_name(k), "minutes": m}
            for k, m in by_list.items()
        ]
    else:
        by = "task"
        items = [
            {"key": tid or "none", "name": task_names.get(tid) or ("纯计时" if tid is None else "已删除任务"), "minutes": m}
            for tid, m in by_task.items()
        ]
    items.sort(key=lambda x: -x["minutes"])
    total = sum(x["minutes"] for x in items)
    for x in items:
        x["pct"] = round(x["minutes"] * 100 / total, 2) if total else 0
    now_day = _parse_day(None, tz_offset_minutes)
    is_current = start_day <= now_day < start_day + timedelta(days=days_n)
    if period == "day":
        range_label = "今天" if is_current else f"{start_day.month}月{start_day.day}日"
    elif period == "week":
        range_label = "本周" if is_current else f"{start_day.month}月{start_day.day}日 - {(start_day + timedelta(days=6)).day}日"
    else:
        range_label = f"{anchor.month}月" if is_current else f"{anchor.year}年{anchor.month}月"
    return {
        "by": by,
        "period": period,
        "items": items[:50],
        "total_minutes": total,
        "range_label": range_label,
        "is_current": is_current,
        "anchor": start_day.isoformat(),
    }


async def _resolve_task_names(task_ids: List[str]) -> dict:
    oids = [ObjectId(t) for t in task_ids if t and is_valid_oid(t)]
    if not oids:
        return {}
    tasks = await Task.find({"_id": {"$in": oids}}).to_list()
    return {str(t.id): t.title for t in tasks}


async def _resolve_task_lists(task_ids: List[str]) -> dict:
    oids = [ObjectId(t) for t in task_ids if t and is_valid_oid(t)]
    if not oids:
        return {}
    tasks = await Task.find({"_id": {"$in": oids}}).to_list()
    return {str(t.id): (str(t.list_id) if t.list_id else None) for t in tasks}


async def _list_name(list_id: str) -> str:
    if list_id == "none":
        return "纯计时"
    if not is_valid_oid(list_id):
        return "已删除清单"
    from app.models.task.task_list import TaskList

    tl = await TaskList.get(ObjectId(list_id))
    return tl.name if tl else "已删除清单"


async def delete_records(owner: str, ids: Optional[List[str]] = None, all_records: bool = False) -> int:
    """删除已完成/已放弃的专注记录（running 不可删）。"""
    conditions = [FocusSession.owner == owner, FocusSession.status != "running"]
    if not all_records:
        valid_ids = [ObjectId(i) for i in (ids or []) if is_valid_oid(i)]
        if not valid_ids:
            return 0
        conditions.append({"_id": {"$in": valid_ids}})
    sessions = await FocusSession.find(*conditions).to_list()
    for s in sessions:
        await s.delete()
    return len(sessions)
