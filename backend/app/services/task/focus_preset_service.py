"""常用专注预设服务（模块级函数，对齐 focus_service 风格）。"""
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.task.focus_preset import FocusPreset
from app.models.task.focus_session import FocusSession
from app.services.case.folder_service import is_valid_oid
from app.services.task import share_service


_VALID_MODES = ("countdown", "stopwatch")


async def _get_preset_or_404(preset_id: str, owner: str) -> FocusPreset:
    if not is_valid_oid(preset_id):
        raise not_found("preset_not_found", "常用专注不存在")
    preset = await FocusPreset.get(ObjectId(preset_id))
    if preset is None or preset.owner != owner:
        raise not_found("preset_not_found", "常用专注不存在")
    return preset


async def _validate_task(task_id: Optional[str], owner: str) -> None:
    if task_id:
        task = await share_service.get_task_or_none(task_id)
        if task is None or task.is_deleted or not await share_service.can_access_task(task, owner):
            raise not_found("task_not_found", "关联任务不存在")


def _validate_mode(mode: str, duration_minutes: int) -> None:
    if mode not in _VALID_MODES:
        raise bad_request("invalid_mode", "计时模式仅支持 countdown / stopwatch")
    if mode == "countdown" and (duration_minutes < 1 or duration_minutes > 180):
        raise bad_request("invalid_duration", "番茄计时时长须在 1~180 分钟之间")


async def create_preset(
    owner: str,
    name: str,
    icon: str = "🍅",
    color: str = "#4f6ef7",
    mode: str = "countdown",
    duration_minutes: int = 25,
    task_id: Optional[str] = None,
    habit_id: Optional[str] = None,
) -> FocusPreset:
    name = (name or "").strip()
    if not name:
        raise bad_request("invalid_name", "名称不能为空")
    _validate_mode(mode, duration_minutes)
    await _validate_task(task_id, owner)
    max_order = (
        await FocusPreset.find(FocusPreset.owner == owner)
        .aggregate([{"$group": {"_id": None, "m": {"$max": "$sort_order"}}}])
        .to_list(1)
    )
    preset = FocusPreset(
        owner=owner,
        name=name,
        icon=icon or "🍅",
        color=color or "#4f6ef7",
        mode=mode,
        duration_minutes=duration_minutes,
        task_id=task_id or None,
        habit_id=habit_id or None,
        sort_order=(max_order[0]["m"] if max_order else 0) + 1,
    )
    await preset.insert()
    return preset


async def update_preset(preset_id: str, owner: str, **fields) -> FocusPreset:
    preset = await _get_preset_or_404(preset_id, owner)
    mode = fields.get("mode", preset.mode)
    duration = fields.get("duration_minutes", preset.duration_minutes)
    _validate_mode(mode, duration)
    if "name" in fields:
        name = (fields["name"] or "").strip()
        if not name:
            raise bad_request("invalid_name", "名称不能为空")
        preset.name = name
    if "icon" in fields and fields["icon"] is not None:
        preset.icon = fields["icon"] or "🍅"
    if "color" in fields and fields["color"]:
        preset.color = fields["color"]
    if "mode" in fields and fields["mode"]:
        preset.mode = fields["mode"]
    if "duration_minutes" in fields and fields["duration_minutes"] is not None:
        preset.duration_minutes = fields["duration_minutes"]
    if "task_id" in fields:
        await _validate_task(fields["task_id"], owner)
        preset.task_id = fields["task_id"] or None
    if "habit_id" in fields:
        preset.habit_id = fields["habit_id"] or None
    if "archived" in fields and fields["archived"] is not None:
        preset.archived = bool(fields["archived"])
    if "sort_order" in fields and fields["sort_order"] is not None:
        preset.sort_order = int(fields["sort_order"])
    preset.updated_at = datetime.now(timezone.utc)
    await preset.save()
    return preset


async def delete_preset(preset_id: str, owner: str) -> None:
    preset = await _get_preset_or_404(preset_id, owner)
    await preset.delete()  # 历史会话保留 preset_id 悬空，统计按会话走不受影响


async def _completed_sessions(preset_id: str) -> List[FocusSession]:
    return await FocusSession.find(
        FocusSession.preset_id == preset_id, FocusSession.status == "completed"
    ).to_list()


async def list_presets(owner: str, archived: bool = False) -> List[dict]:
    """坚持中/已归档列表，附带累计专注秒（completed 会话求和）。"""
    presets = (
        await FocusPreset.find(
            FocusPreset.owner == owner, FocusPreset.archived == archived
        )
        .sort("sort_order")
        .to_list()
    )
    if not presets:
        return []
    ids = [str(p.id) for p in presets]
    agg = (
        await FocusSession.find(
            {"preset_id": {"$in": ids}}, FocusSession.status == "completed"
        )
        .aggregate([
            {"$group": {"_id": "$preset_id", "s": {"$sum": "$actual_seconds"}}}
        ])
        .to_list(len(ids))
    )
    seconds_map = {row["_id"]: row["s"] for row in agg}
    return [
        {**preset.model_dump(), "id": str(preset.id), "total_seconds": seconds_map.get(str(preset.id), 0)}
        for preset in presets
    ]


async def preset_stats(
    preset_id: str,
    owner: str,
    tz_offset_minutes: int = 0,
    week_start: Optional[date] = None,
) -> dict:
    """详情三卡（专注天数/今日时长/总时长）+ 周条图（周一起 7 天分钟）。"""
    await _get_preset_or_404(preset_id, owner)
    sessions = await _completed_sessions(preset_id)

    total_seconds = sum(s.actual_seconds for s in sessions)
    local_now = datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)
    today = local_now.date()
    days = {
        (s.started_at + timedelta(minutes=tz_offset_minutes)).date() for s in sessions
    }
    today_seconds = sum(
        s.actual_seconds
        for s in sessions
        if (s.started_at + timedelta(minutes=tz_offset_minutes)).date() == today
    )

    # 周条图：默认本周一（本地）；week_start 由前端传当周周一（本地日期）
    monday = week_start or (today - timedelta(days=today.weekday()))
    week_start_utc = datetime.combine(monday, datetime.min.time()) - timedelta(
        minutes=tz_offset_minutes
    )
    week_days = [0] * 7
    for s in sessions:
        start_local_date = (s.started_at + timedelta(minutes=tz_offset_minutes)).date()
        idx = (start_local_date - monday).days
        if 0 <= idx < 7:
            week_days[idx] += s.actual_seconds // 60
    week_end = monday + timedelta(days=6)
    week_label = f"{monday.month}月{monday.day}日 - {week_end.month}月{week_end.day}日"
    return {
        "total_minutes": total_seconds // 60,
        "today_minutes": today_seconds // 60,
        "days": len(days),
        "week_days": week_days,
        "week_label": week_label,
        "week_start": monday.isoformat(),
    }
