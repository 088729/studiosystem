from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


class WikiVault(Document):
    name: Indexed(str)
    description: str = ""
    owner: str
    repo_dir: str  # 服务端磁盘目录名（uuid），真实路径 = WIKI_REPO_ROOT/repo_dir，接口层永不直接接收
    remote_url: Optional[str] = None
    default_branch: str = "main"
    visibility: str = "internal"  # internal / private（字段预留，一期仅 internal）
    auto_commit_interval: int = 300  # 秒，0 表示关闭
    status: str = "ready"  # ready / cloning / indexing / importing / error
    status_message: str = ""  # error 时的原因说明
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "wiki_vaults"
        indexes = [
            # 库名在「未软删」集合内唯一
            IndexModel(
                [("name", 1)],
                unique=True,
                partialFilterExpression={"is_deleted": False},
            ),
            IndexModel([("owner", 1)]),
        ]
