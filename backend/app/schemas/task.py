from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.models.task.task import Attachment, RecurrenceRule, Reminder
from app.models.task.task_list import Member


# ---------- 清单 ----------

class TaskListCreate(BaseModel):
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None
    group: Optional[str] = None
    kind: str = "task"  # task | note


class TaskListUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    group: Optional[str] = None
    kind: Optional[str] = None  # 显式传 null = 转回任务清单
    is_archived: Optional[bool] = None


class TaskListOut(BaseModel):
    id: str
    name: str
    owner: str
    members: List[Member] = []
    is_shared: bool = False  # 对当前用户而言是否为共享给我的清单
    color: str
    icon: Optional[str] = None
    group: Optional[str] = None
    board_groups: List[str] = []  # 看板分组列（有序）
    kind: str = "task"  # task | note
    sort_order: int
    is_archived: bool
    created_at: datetime


class ListGroupCreate(BaseModel):
    name: str
    index: Optional[int] = None  # 插入位置（0-based），缺省=末尾追加


class ListGroupRename(BaseModel):
    from_name: str
    to_name: str


class ListGroupMove(BaseModel):
    name: str
    from_list_id: Optional[str] = None  # null = 收集箱
    to_list_id: Optional[str] = None  # null = 收集箱


class TaskListResponse(BaseModel):
    items: List[TaskListOut]


# ---------- 标签 ----------

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None


class TagOut(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: int
    created_at: datetime


class TagResponse(BaseModel):
    items: List[TagOut]


# ---------- 附件 ----------

class AttachmentIn(BaseModel):
    resource_id: str  # resourceplatform 相对路径（上传响应的 path）
    name: str
    content_type: str
    size: int


# ---------- 任务 ----------

class TaskCreate(BaseModel):
    title: str
    list_id: Optional[str] = None
    group: Optional[str] = None  # 看板分组名（须属于 list_id 的 board_groups）
    parent_id: Optional[str] = None
    note: Optional[str] = None
    assignee: Optional[str] = None
    priority: int = 0
    tags: List[str] = []
    due_at: Optional[datetime] = None
    all_day: bool = False
    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    reminders: List[Reminder] = []
    persistent_reminder: bool = False
    recurrence: Optional[RecurrenceRule] = None
    case_map_id: Optional[str] = None
    case_node_id: Optional[str] = None
    is_pinned: bool = False
    is_note: Optional[bool] = None  # 显式传入优先；缺省时跟随所属清单 kind（收集箱=task）


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    note: Optional[str] = None
    group: Optional[str] = None  # 看板分组（看板拖拽换列），显式传 null = 未分组列
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    due_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    reminders: Optional[List[Reminder]] = None
    persistent_reminder: Optional[bool] = None
    recurrence: Optional[RecurrenceRule] = None
    assignee: Optional[str] = None
    case_map_id: Optional[str] = None
    case_node_id: Optional[str] = None
    is_pinned: Optional[bool] = None
    parent_id: Optional[str] = None  # 拖动转子任务：传入父任务 id；显式传 null = 转回普通任务
    is_note: Optional[bool] = None  # 任务 ↔ 笔记 转换（有子任务不可转笔记，400）


class TaskMove(BaseModel):
    list_id: Optional[str] = None


class TaskSort(BaseModel):
    sort_order: Optional[int] = None
    before_task_id: Optional[str] = None
    after_task_id: Optional[str] = None  # 落尾/落中间由后端算 sort_order，避免前端硬编码步长冲突（B4）


class TaskBatch(BaseModel):
    ids: List[str]
    action: str  # complete | delete | move | priority | due | pin | tags
    payload: dict = {}


class TaskComplete(BaseModel):
    done: bool


class TaskOut(BaseModel):
    id: str
    title: str
    note: Optional[str]
    list_id: Optional[str]
    group: Optional[str] = None
    parent_id: Optional[str]
    owner: str
    assignee: Optional[str]
    status: str
    completed_at: Optional[datetime]
    priority: int
    tags: List[str]
    due_at: Optional[datetime]
    all_day: bool
    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    reminders: List[Reminder]
    persistent_reminder: bool = False
    attachments: List[Attachment] = []
    recurrence: Optional[RecurrenceRule]
    next_due: Optional[datetime] = None
    occurrences_completed: int = 0
    case_map_id: Optional[str]
    case_node_id: Optional[str]
    is_pinned: bool = False
    is_note: bool = False
    sort_order: int
    subtask_total: int = 0
    subtask_done: int = 0
    created_at: datetime
    updated_at: datetime


class TaskDetailOut(TaskOut):
    subtasks: List[TaskOut] = []
    case_map_title: Optional[str] = None
    case_node_text: Optional[str] = None


class TaskItemsResponse(BaseModel):
    items: List[TaskOut]


# ---------- 摘要（对齐主流待办应用「摘要」智能清单） ----------

class SummaryPreviewIn(BaseModel):
    range: str = "this_week"  # today | yesterday | this_week | last_week | this_month | custom
    start: Optional[datetime] = None  # custom 范围的起点（客户端时区）
    end: Optional[datetime] = None  # custom 范围的终点（开区间，客户端时区）
    list_ids: List[str] = []  # 清单 id 过滤，"inbox" = 收集箱；空 = 全部
    statuses: List[str] = ["done", "todo"]  # 汇总哪些状态
    tags: List[str] = []  # 任一标签命中即入选
    priorities: List[int] = []
    assignees: List[str] = []
    group_by: str = "status"  # status | list
    show: List[str] = ["date"]  # date | list | priority（markdown 里显示的字段）
    tz_offset_minutes: int = 0  # 本地 − UTC（东八区 +480）


# ---------- 筛选器 ----------


class TaskFilterCreate(BaseModel):
    name: str
    lists: List[str] = []
    tags: List[str] = []
    priorities: List[int] = []
    due_range: str = "any"
    status: str = "todo"
    keyword: str = ""


class TaskFilterUpdate(BaseModel):
    name: Optional[str] = None
    lists: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    priorities: Optional[List[int]] = None
    due_range: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None


class TaskFilterOut(BaseModel):
    id: str
    name: str
    lists: List[str] = []
    tags: List[str] = []
    priorities: List[int] = []
    due_range: str = "any"
    status: str = "todo"
    keyword: str = ""
    sort_order: int = 0
    count: int = 0  # 命中任务数（侧栏计数徽标）


class TaskFilterResponse(BaseModel):
    items: List[TaskFilterOut]


# ---------- 番茄钟 ----------


class FocusStart(BaseModel):
    task_id: Optional[str] = None
    planned_minutes: int = 25
    preset_id: Optional[str] = None  # 常用专注预设（带关联任务时沿用）
    habit_id: Optional[str] = None  # 关联习惯（完成时自动打卡）


class FocusSessionOut(BaseModel):
    id: str
    task_id: Optional[str]
    preset_id: Optional[str] = None
    habit_id: Optional[str] = None
    owner: str
    planned_minutes: int
    actual_seconds: int
    status: str
    paused_at: Optional[datetime] = None  # 暂停中=暂停开始时刻（刷新后恢复暂停态用）
    paused_seconds: int = 0  # 累计已恢复暂停秒
    note: str = ""
    started_at: datetime
    ended_at: Optional[datetime]


class FocusUpdate(BaseModel):
    """专注中：调 planned_minutes（±调时）；结束后：改 actual_seconds / note。"""

    planned_minutes: Optional[int] = Field(None, ge=1, le=600)
    actual_seconds: Optional[int] = Field(None, ge=0, le=86400)
    note: Optional[str] = Field(None, max_length=5000)


class FocusRecordCreate(BaseModel):
    """补记一条已完成专注记录。"""

    task_id: Optional[str] = None
    preset_id: Optional[str] = None
    planned_minutes: int = Field(25, ge=1, le=600)
    actual_seconds: int = Field(..., ge=1, le=86400)
    started_at: datetime
    note: str = Field("", max_length=5000)


class FocusRecordsDelete(BaseModel):
    """删除专注记录：指定 ids 或 all 清空（running 不可删）。"""

    ids: Optional[List[str]] = None
    all: bool = False


# ---------- 常用专注预设 ----------


class FocusPresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    icon: str = Field("🍅", max_length=8)
    color: str = Field("#4f6ef7", max_length=20)
    mode: str = "countdown"  # countdown | stopwatch
    duration_minutes: int = Field(25, ge=1, le=180)
    task_id: Optional[str] = None
    habit_id: Optional[str] = None


class FocusPresetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    icon: Optional[str] = Field(None, max_length=8)
    color: Optional[str] = Field(None, max_length=20)
    mode: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=180)
    task_id: Optional[str] = None
    habit_id: Optional[str] = None
    archived: Optional[bool] = None
    sort_order: Optional[int] = None


class FocusPresetOut(BaseModel):
    id: str
    owner: str
    name: str
    icon: str
    color: str
    mode: str
    duration_minutes: int
    task_id: Optional[str]
    habit_id: Optional[str] = None
    archived: bool
    sort_order: int
    created_at: datetime
    total_seconds: int = 0  # 累计专注秒（completed 会话求和）


# ---------- 习惯打卡 ----------


class HabitCreate(BaseModel):
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None  # 习惯图标 key
    freq: str = "daily"  # daily | weekly
    target_per_day: int = 1
    target_per_week: int = 7
    start_date: Optional[str] = None  # YYYY-MM-DD
    group: Optional[str] = None
    goal_type: str = "amount"  # check=当天完成打卡 | amount=当天完成一定量
    checkin_mode: str = "auto"  # auto=自动记录(+1) | manual=手动输入量 | all=完成全部
    reminders: List[str] = []  # 提醒时刻 HH:mm 列表
    auto_log: bool = True  # 打卡后自动弹出打卡日志（心情/笔记）
    motto: str = ""  # 鼓励语


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None  # 习惯图标 key
    freq: Optional[str] = None
    target_per_day: Optional[int] = None
    target_per_week: Optional[int] = None
    start_date: Optional[str] = None
    group: Optional[str] = None
    checkin_style: Optional[str] = None  # check=对勾 | icon=习惯图标
    is_archived: Optional[bool] = None
    goal_type: Optional[str] = None
    checkin_mode: Optional[str] = None
    reminders: Optional[List[str]] = None
    auto_log: Optional[bool] = None
    motto: Optional[str] = None


class HabitOut(BaseModel):
    id: str
    name: str
    color: str
    icon: str = "smile"
    freq: str = "daily"
    target_per_day: int = 1
    target_per_week: int = 7
    start_date: Optional[str] = None
    group: Optional[str] = None
    checkin_style: str = "check"  # check=对勾 | icon=习惯图标
    is_archived: bool
    goal_type: str = "amount"
    checkin_mode: str = "auto"
    reminders: List[str] = []
    auto_log: bool = True
    motto: str = ""
    today_checked: bool = False  # 今日是否已达标（count >= target_per_day）
    today_skipped: bool = False  # 今日是否已跳过（存在 skipped=True 且未达标的日志）
    today_count: int = 0
    streak: int = 0
    total_days: int = 0  # 累计打卡天数（count>0 且未跳过的日期数）
    week_bitmap: List[bool] = []  # 最近 7 天达标位图（旧→新，最后一位是今天）
    created_at: datetime


class HabitCheckin(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD，缺省按 tz_offset_minutes 算今天
    amount: Optional[int] = Field(None, ge=1, le=999)  # 手动记录模式：本次完成量（缺省 +1）
    note: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)  # 心情 1~5，传入才覆盖
    meta_only: bool = False  # True=只写心情/日志（打卡后自动弹层），不增加 count


class HabitSkip(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD，缺省按 tz_offset_minutes 算今天


# ---------- 评论 ----------


class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: str
    task_id: str
    author: str
    content: str
    created_at: datetime


# ---------- 任务默认值设置 ----------


class TaskSettingsUpdate(BaseModel):
    default_list_id: Optional[str] = None
    default_due: Optional[str] = None  # none | today | tomorrow
    default_priority: Optional[int] = None
    default_reminder_minutes: Optional[Union[Literal["end"], int]] = None  # 相对分钟 | "end"=结束时
    default_reminder_allday: Optional[str] = None  # none | same_day_9am | prev_day_8pm
    default_range_minutes: Optional[int] = None
    default_tags: Optional[list[str]] = None
    daily_reminder_enabled: Optional[bool] = None
    daily_reminder_time: Optional[str] = None
    web_notification: Optional[bool] = None
    persistent_reminder_all: Optional[bool] = None
    reminder_sound: Optional[Literal["none", "default", "music_box", "african_drum", "beep", "brick", "bell", "crystal", "ladder"]] = None  # 提醒铃声
    show_notification_detail: Optional[bool] = None  # 显示通知详情
    completion_sound: Optional[Literal["none", "ding", "waterdrop", "knock", "spiral"]] = None  # 完成提示音
    reminder_volume: Optional[int] = Field(None, ge=0, le=100)  # 提醒音量 0-100
    priority_sound_enabled: Optional[bool] = None  # 按优先级设置提醒
    priority_sound_high: Optional[Literal["none", "default", "music_box", "african_drum", "beep", "brick", "bell", "crystal", "ladder"]] = None
    priority_sound_medium: Optional[Literal["none", "default", "music_box", "african_drum", "beep", "brick", "bell", "crystal", "ladder"]] = None
    priority_sound_low: Optional[Literal["none", "default", "music_box", "african_drum", "beep", "brick", "bell", "crystal", "ladder"]] = None
    priority_sound_none: Optional[Literal["none", "default", "music_box", "african_drum", "beep", "brick", "bell", "crystal", "ladder"]] = None
    show_lunar: Optional[bool] = None
    time_format: Optional[Literal["24h", "12h"]] = None  # 时间格式
    week_start: Optional[Literal["sunday", "monday"]] = None  # 每周开始于
    show_week_number: Optional[bool] = None
    show_holiday: Optional[bool] = None
    show_timezone: Optional[bool] = None
    inbox_board_groups: Optional[list[str]] = None  # 收集箱自定义分组
    summary_config: Optional[dict] = None  # 摘要配置
    summary_templates: Optional[list[dict]] = None  # 摘要配置模板
    note_templates: Optional[list[dict]] = None  # 笔记模板
    focus_config: Optional[dict] = None  # 专注设置（番茄/短休/长休时长、提示音等）


class TaskSettingsOut(BaseModel):
    default_list_id: Optional[str] = None
    default_due: str = "none"
    default_priority: int = 0
    default_reminder_minutes: Optional[Union[Literal["end"], int]] = None  # 相对分钟 | "end"=结束时
    default_reminder_allday: str = "none"
    default_range_minutes: int = 60
    default_tags: list[str] = []
    daily_reminder_enabled: bool = False
    daily_reminder_time: str = "09:00"
    web_notification: bool = False
    persistent_reminder_all: bool = False
    reminder_sound: str = "default"  # 提醒铃声
    show_notification_detail: bool = True
    completion_sound: str = "ding"
    reminder_volume: int = 80
    priority_sound_enabled: bool = False
    priority_sound_high: str = "default"
    priority_sound_medium: str = "default"
    priority_sound_low: str = "default"
    priority_sound_none: str = "default"
    show_lunar: bool = False
    time_format: str = "24h"
    week_start: str = "sunday"
    show_week_number: bool = False
    show_holiday: bool = False
    show_timezone: bool = False
    inbox_board_groups: list[str] = []  # 收集箱自定义分组
    summary_config: dict = {}  # 摘要配置
    summary_templates: list[dict] = []  # 摘要配置模板
    note_templates: list[dict] = []  # 笔记模板（有序）
    focus_config: dict = {}  # 专注设置（番茄/短休/长休时长、提示音等）
