from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class FocusPreset(Document):
    """常用专注预设：名称 + 彩圆图标 + 计时模式 + 关联任务，行 ▶ 一键开始。
    会话通过 FocusSession.preset_id 回挂，用于累计时长/天数/周条图统计。"""

    owner: str
    name: str
    icon: str = "🍅"  # emoji 图标，或文字模式下单个字符
    color: str = "#4f6ef7"  # 彩圆底色
    mode: str = "countdown"  # countdown | stopwatch
    duration_minutes: int = 25  # countdown 模式的计划时长
    task_id: Optional[str] = None  # 关联任务（可空 = 纯计时）
    habit_id: Optional[str] = None  # 关联习惯（开始专注完成时自动打卡）
    archived: bool = False  # 归档后不出现在坚持中
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "focus_presets"
        indexes = [
            IndexModel("owner"),
            IndexModel([("owner", 1), ("archived", 1)]),
        ]
