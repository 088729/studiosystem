from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field, field_validator
from pymongo import IndexModel


class Member(BaseModel):
    username: str
    role: str = "viewer"  # viewer | editor


class TaskList(Document):
    name: str
    owner: str
    kind: str = "task"  # task | note（笔记清单：新建项默认 is_note=True，对齐主流待办应用笔记清单）
    members: List[Member] = []  # 共享成员（不含 owner），role ∈ viewer|editor
    color: str = "#4f6ef7"
    icon: Optional[str] = None  # Lucide 图标 key（对齐主流待办应用图标），null = 仅色点
    group: Optional[str] = None  # 分组名（P3 清单分组），None = 未分组平铺
    board_groups: List[str] = []  # 看板分组列（有序，对齐主流待办应用看板「添加分组」），任务按 group 名归列
    sort_order: int = 0
    is_archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("members", mode="before")
    @classmethod
    def _coerce_legacy_members(cls, v):
        """存量兼容：旧数据 members 为 List[str]，读取时视为 viewer。"""
        return [Member(username=m) if isinstance(m, str) else m for m in (v or [])]

    class Settings:
        name = "task_lists"
        indexes = [
            IndexModel("owner"),
            IndexModel("sort_order"),
        ]
