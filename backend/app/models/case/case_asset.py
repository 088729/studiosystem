from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class CaseAsset(Document):
    map_id: Indexed(str)
    node_id: str
    url: str
    file_type: str
    file_size: int
    file_hash: Indexed(str)
    relative_path: str
    refer_count: int = 1
    is_orphan: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "case_assets"
        indexes = [
            "map_id",
            "file_hash",
            "is_orphan",
        ]
