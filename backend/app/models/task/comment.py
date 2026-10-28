from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class TaskComment(Document):
    """任务评论。可见性跟随任务可见性；删除为物理删。"""

    task_id: str
    author: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "task_comments"
        indexes = [
            IndexModel("task_id"),
        ]
