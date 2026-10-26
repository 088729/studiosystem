from datetime import datetime, timezone
from typing import Any, Dict

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class CaseVersion(Document):
    map_id: str
    version_no: int
    root: Dict[str, Any]
    changelog: str = "系统自动保存"
    operator_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "case_versions"
        indexes = [
            IndexModel([("map_id", 1), ("version_no", 1)], unique=True),
        ]
