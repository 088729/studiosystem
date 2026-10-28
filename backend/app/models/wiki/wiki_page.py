from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


class WikiPage(Document):
    """每篇 .md 文档一行索引。正文不落库，body 仅为可重建的派生搜索索引。"""

    vault_id: Indexed(str)
    path: str  # 仓库内相对路径（POSIX 风格，统一 /）
    title: str
    folder: str  # 所在目录，根为 ""
    tags: List[str] = []
    size: int = 0
    body: str = ""  # 去 Markdown 语义的纯文本，仅服务全文搜索（可随 rebuild-index 重建）
    last_commit_at: Optional[datetime] = None
    locked_by: Optional[str] = None  # 持锁人（用户名，展示用）
    lock_token: Optional[str] = None  # 持锁令牌（operator@windowId，判定归属用）
    locked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "wiki_pages"
        indexes = [
            IndexModel([("vault_id", 1), ("path", 1)], unique=True),
            IndexModel([("vault_id", 1), ("folder", 1)]),
            IndexModel([("vault_id", 1), ("tags", 1)]),
        ]
