from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import ConfigDict, Field
from pymongo import IndexModel


class Habit(Document):
    """习惯打卡：每日习惯定义。"""

    name: str
    owner: str
    color: str = "#4f6ef7"
    freq: str = "daily"  # daily | weekly
    target_per_day: int = 1  # 每日目标打卡次数
    target_per_week: int = 7  # weekly 时每周需达标天数
    start_date: Optional[str] = None  # YYYY-MM-DD
    group: Optional[str] = None  # 分组名
    checkin_style: str = "check"  # 打卡样式：check=对勾 | icon=习惯图标（对齐主流待办应用）
    goal_type: str = "amount"  # 目标类型：check=当天完成打卡 | amount=当天完成一定量
    checkin_mode: str = "auto"  # 打卡方式：auto=自动记录(+1) | manual=手动输入量 | all=完成全部
    reminders: List[str] = []  # 打卡提醒时刻 HH:mm（对齐主流待办应用多时段提示）
    auto_log: bool = True  # 打卡后自动弹出打卡日志（心情/笔记）
    motto: str = ""  # 鼓励语（自定义习惯「写点鼓励自己的话」）
    icon: str = "smile"  # 习惯图标 key（对齐主流待办应用图标库），见前端 utils/habitIcons.js
    is_archived: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "habits"
        indexes = [
            IndexModel("owner"),
        ]


class HabitLog(Document):
    """习惯打卡记录。date 为客户端本地日（YYYY-MM-DD）。"""

    habit_id: str
    owner: str
    date: str  # YYYY-MM-DD
    # 当日打卡次数。DB 字段保持 "count"（alias），属性名避免遮蔽 Document.count
    checkin_count: int = Field(default=1, alias="count")
    skipped: bool = False  # 跳过标记：当天不算打卡，也不打断连续 streak（对齐主流待办应用「跳过」语义）
    mood: Optional[int] = None  # 心情 1~5：1=大哭 2=难过 3=平静 4=不错 5=开心
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        name = "habit_logs"
        indexes = [
            IndexModel([("habit_id", 1), ("date", 1)]),
            IndexModel("owner"),
        ]
