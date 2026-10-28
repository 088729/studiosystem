from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Tag(Document):
    """标签实体：颜色/层级/侧栏管理；任务的 tags 数组按名称引用。"""

    name: str
    owner: str
    color: Optional[str] = None  # null = 无颜色
    parent_id: Optional[str] = None  # 上级标签 ID；null = 顶级标签（只允许一级层级）
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tags"
        indexes = [
            IndexModel("owner"),
            IndexModel("parent_id"),
        ]
