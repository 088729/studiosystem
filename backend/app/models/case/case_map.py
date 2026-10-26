from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


class CaseMap(Document):
    title: str
    owner: str
    folder_id: Optional[Indexed(str)] = None
    is_deleted: bool = False
    current_version: int = 1
    temp_content: Optional[Dict[str, Any]] = None
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "case_maps"
        indexes = [
            IndexModel([("folder_id", 1), ("is_deleted", 1)]),
        ]
