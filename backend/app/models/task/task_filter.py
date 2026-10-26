from datetime import datetime, timezone
from typing import List

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class TaskFilter(Document):
    """用户保存的自定义筛选器（侧栏「过滤器」分组）。"""

    owner: str
    name: str
    lists: List[str] = []  # 清单 id，空 = 全部
    tags: List[str] = []  # 任一命中
    priorities: List[int] = []  # 任一命中
    due_range: str = "any"  # any | overdue | today | next7 | no_date
    status: str = "todo"  # todo | done | any
    keyword: str = ""  # 标题模糊
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "task_filters"
        indexes = [
            IndexModel("owner"),
            IndexModel("sort_order"),
        ]
