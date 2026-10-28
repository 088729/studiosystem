from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import FocusPresetCreate, FocusPresetOut, FocusPresetUpdate
from app.services.task import focus_preset_service

router = APIRouter()


def _preset_out(p: dict) -> FocusPresetOut:
    return FocusPresetOut(**p)


@router.get("")
async def list_presets(
    archived: bool = False,
    current_user: User = Depends(require_perm("task:view")),
):
    """坚持中 / 已归档列表（含累计专注秒）。"""
    items = await focus_preset_service.list_presets(current_user.username, archived)
    return {"items": [_preset_out(p) for p in items]}


@router.post("", response_model=FocusPresetOut)
async def create_preset(
    data: FocusPresetCreate,
    current_user: User = Depends(require_perm("task:run")),
):
    preset = await focus_preset_service.create_preset(
        current_user.username,
        data.name,
        data.icon,
        data.color,
        data.mode,
        data.duration_minutes,
        data.task_id,
        data.habit_id,
    )
    return _preset_out({**preset.model_dump(), "id": str(preset.id), "total_seconds": 0})


@router.patch("/{preset_id}", response_model=FocusPresetOut)
async def update_preset(
    preset_id: str,
    data: FocusPresetUpdate,
    current_user: User = Depends(require_perm("task:run")),
):
    preset = await focus_preset_service.update_preset(
        preset_id, current_user.username, **data.model_dump(exclude_unset=True)
    )
    items = await focus_preset_service.list_presets(
        current_user.username, preset.archived
    )
    for p in items:
        if p["id"] == str(preset.id):
            return _preset_out(p)
    return _preset_out({**preset.model_dump(), "id": str(preset.id), "total_seconds": 0})


@router.delete("/{preset_id}")
async def delete_preset(
    preset_id: str,
    current_user: User = Depends(require_perm("task:run")),
):
    await focus_preset_service.delete_preset(preset_id, current_user.username)
    return {"ok": True}


@router.get("/{preset_id}/stats")
async def preset_stats(
    preset_id: str,
    tz_offset_minutes: int = 0,
    week_start: Optional[date] = None,
    current_user: User = Depends(require_perm("task:view")),
):
    """详情三卡（专注天数/今日时长/总时长）+ 周条图（周一起 7 天分钟）。"""
    return await focus_preset_service.preset_stats(
        preset_id, current_user.username, tz_offset_minutes, week_start
    )
