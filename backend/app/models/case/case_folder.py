from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class CaseFolder(Document):
    name: str
    parent_id: Optional[Indexed(str)] = None
    depth: int = 0
    owner: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "case_folders"
        indexes = [
            "parent_id",
        ]
