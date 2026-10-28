from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel


class Reminder(BaseModel):
    """绝对时间提醒（相对提醒由前端换算后落库）。offset_minutes 非空表示相对提醒，
    改 due_at 时前端据此重算 at。"""

    at: datetime
    triggered: bool = False
    notified: bool = False
    offset_minutes: Optional[int] = None


class Attachment(BaseModel):
    """任务附件：仅存 resourceplatform 引用（resource_id = 相对路径）与元信息，不存二进制。"""

    resource_id: str
    name: str
    content_type: str
    size: int
    uploaded_by: str
    url: Optional[str] = None  # resourceplatform 返回的公开访问 URL（本地下载兜底挂载后可直接用）
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecurrenceRule(BaseModel):
    """重复规则。by_weekday 空 = 按当前 due_at 的星期几；by_monthday 空 = 按 due_at 的日号，
    月末 clamp 到当月最后一天（如 1/31 → 2/28）。"""

    freq: str = "daily"  # daily | weekly | monthly | yearly
    interval: int = 1
    by_weekday: List[int] = []  # weekly 用，0=周一 ... 6=周日
    by_monthday: List[int] = []  # monthly 用，1~31
    end_type: str = "never"  # never | by_date | after_count
    end_date: Optional[datetime] = None
    count: Optional[int] = None
    occurrences_completed: int = 0  # 已完成次数（后端维护，after_count 判定依据）


class Task(Document):
    title: str
    note: Optional[str] = None
    list_id: Optional[str] = None  # null = 收集箱
    group: Optional[str] = None  # 看板分组名（所属清单 board_groups 之一），null = 未分组列
    parent_id: Optional[str] = None  # 非空即子任务（仅允许一级）
    owner: str
    assignee: Optional[str] = None
    status: str = "todo"  # todo | done
    completed_at: Optional[datetime] = None
    priority: int = 0  # 0 无 / 1 低 / 2 中 / 3 高
    tags: List[str] = []
    due_at: Optional[datetime] = None
    all_day: bool = False
    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None  # 时长（分钟，1~1440），配合日历时间块
    reminders: List[Reminder] = []
    persistent_reminder: bool = False  # 持续提醒：通知被关掉但未处理时，每 2 分钟再次弹出（对齐主流待办应用）
    attachments: List[Attachment] = []
    recurrence: Optional[RecurrenceRule] = None
    case_map_id: Optional[str] = None
    case_node_id: Optional[str] = None
    is_pinned: bool = False  # 置顶标记（P1），置顶任务排清单顶部，排序由前端处理
    is_note: bool = False  # 笔记：无完成概念（status 恒 todo，UI 隐藏勾选），可对转换（对齐主流待办应用笔记）
    sort_order: int = 0
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"
        indexes = [
            IndexModel([("list_id", 1), ("is_deleted", 1)]),
            IndexModel("parent_id"),
            IndexModel("due_at"),
            IndexModel("owner"),
            IndexModel("case_map_id"),
            IndexModel("reminders.at"),  # 多键索引，提醒循环扫描
        ]
