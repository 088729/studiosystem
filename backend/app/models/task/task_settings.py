from datetime import datetime, timezone
from typing import Literal, Optional, Union

from beanie import Document
from pydantic import Field, field_validator
from pymongo import IndexModel


class TaskSettings(Document):
    """per-user 任务默认值（默认清单/日期/优先级/提醒），唯一键 owner。"""

    owner: str
    default_list_id: Optional[str] = None  # null = 收集箱
    default_due: str = "none"  # none | today | tomorrow
    default_priority: int = 0  # 0 无 / 1 低 / 2 中 / 3 高
    default_reminder_minutes: Optional[Union[Literal["end"], int]] = None  # 相对分钟 | "end"=结束时，null = 无（有时间的任务）
    default_reminder_allday: str = "none"  # 全天任务默认提醒：none | same_day_9am | prev_day_8pm
    default_range_minutes: int = 60  # 默认时间段时长（分钟），日期弹层时间段 Tab 预填用
    default_tags: list[str] = Field(default_factory=list)  # 默认标签
    # ---------- 提醒与通知（设置-提醒与通知，对齐主流待办应用） ----------
    daily_reminder_enabled: bool = False  # 每日提醒开关
    daily_reminder_time: str = "09:00"  # 每日提醒时间（HH:mm，前端到点弹汇总通知）
    web_notification: bool = False  # 网页提醒：授权后同时发浏览器系统通知
    persistent_reminder_all: bool = False  # 全局持续提醒：所有任务提醒被关掉未处理时定时重弹
    reminder_sound: str = "default"  # 提醒铃声：none | default | music_box | african_drum | beep | brick | bell | crystal | ladder（前端合成）
    show_notification_detail: bool = True  # 显示通知详情：关闭后系统通知不展示任务标题（隐私）
    completion_sound: str = "ding"  # 完成提示音：none | ding(叮) | waterdrop(水滴) | knock(敲击) | spiral(螺旋)（前端合成）
    reminder_volume: int = 80  # 提醒音量 0-100（前端播放时按百分比缩放）
    priority_sound_enabled: bool = False  # 按优先级设置提醒：开启后按任务优先级分别选铃声
    priority_sound_high: str = "default"  # 高优先级铃声
    priority_sound_medium: str = "default"  # 中优先级铃声
    priority_sound_low: str = "default"  # 低优先级铃声
    priority_sound_none: str = "default"  # 无优先级铃声
    # ---------- 日期与时间（设置-日期与时间，对齐主流待办应用） ----------
    show_lunar: bool = False  # 显示农历：日历格子内显示对应农历日期
    time_format: str = "24h"  # 时间格式：24h=24小时制 | 12h=12小时制
    week_start: str = "sunday"  # 每周开始于：sunday | monday
    show_week_number: bool = False  # 显示周数：日历左侧显示周序号
    show_holiday: bool = False  # 显示节假日调休：日历格子角标 休/班
    show_timezone: bool = False  # 时区：时间选择界面可选时区，按所选时区解释输入时间
    # ---------- 收集箱自定义分组（对齐主流待办应用：收集箱支持分组管理） ----------
    inbox_board_groups: list[str] = Field(default_factory=list)  # 收集箱自定义分组（有序），list_id=null 任务的 group 须属其中
    # ---------- 摘要（对齐主流待办应用：智能清单「摘要」，配置/模板 per-user） ----------
    summary_config: dict = Field(default_factory=dict)  # 上次使用的筛选/显示配置
    summary_templates: list[dict] = Field(default_factory=list)  # 摘要配置模板 [{name, config}]
    note_templates: list[dict] = Field(default_factory=list)  # 笔记模板 [{name, content_html}]（对齐主流待办应用笔记模板）
    focus_config: dict = Field(default_factory=dict)  # 专注设置（番茄/短休/长休分钟、提示音等；对齐主流待办应用专注设置）
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("completion_sound", mode="before")
    @classmethod
    def _coerce_completion_sound(cls, v):
        # 兼容旧版布尔存储：True→ding，False→none
        if isinstance(v, bool):
            return "ding" if v else "none"
        return v

    class Settings:
        name = "task_settings"
        indexes = [IndexModel("owner", unique=True)]
