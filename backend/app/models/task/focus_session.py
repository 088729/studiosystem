from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class FocusSession(Document):
    """番茄钟专注会话。同一用户同时只允许一个 running 会话。"""

    task_id: Optional[str] = None  # 关联任务（可空 = 纯计时）
    preset_id: Optional[str] = None  # 常用专注预设（可空）
    habit_id: Optional[str] = None  # 关联习惯（完成时自动打卡）
    owner: str
    planned_minutes: int = 25
    actual_seconds: int = 0  # finish/abandon 时写入（扣除暂停时长）
    status: str = "running"  # running | completed | abandoned
    paused_at: Optional[datetime] = None  # 暂停中=暂停开始时刻；运行中=None
    paused_seconds: int = 0  # 累计暂停秒数（已恢复的部分）
    note: str = ""  # 专注笔记
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    class Settings:
        name = "focus_sessions"
        indexes = [
            IndexModel("owner"),
            IndexModel([("owner", 1), ("started_at", 1)]),
            IndexModel("task_id"),
            IndexModel("preset_id"),
        ]
