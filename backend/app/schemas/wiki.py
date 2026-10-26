from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- Vault ----

class VaultCreate(BaseModel):
    name: str
    description: str = ""
    remote_url: Optional[str] = None
    auto_commit_interval: int = 300


class VaultUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    remote_url: Optional[str] = None
    auto_commit_interval: Optional[int] = None
    visibility: Optional[str] = None


class VaultOut(BaseModel):
    id: str
    name: str
    description: str
    owner: str
    remote_url: Optional[str] = None
    default_branch: str
    auto_commit_interval: int
    status: str = "ready"  # ready / cloning / indexing / importing / error
    status_message: str = ""
    created_at: datetime
    updated_at: datetime


class ImportDirIn(BaseModel):
    path: str  # 服务器本地目录绝对路径
    name: Optional[str] = None


class VaultDetailOut(VaultOut):
    changes: List[dict] = []
    doc_count: int = 0
    rebuild: Optional[dict] = None


# ---- Page ----

class PageCreate(BaseModel):
    path: str
    content: str = ""


class PageSave(BaseModel):
    path: str
    content: str
    # 窗口级锁令牌：与本窗口持锁令牌一致才允许保存（防止覆盖其他窗口的编辑）
    holder: Optional[str] = None


class PageMove(BaseModel):
    src: str
    dst: str


class PageOut(BaseModel):
    path: str
    title: str


class TreeNode(BaseModel):
    type: str  # folder / page
    name: str
    path: str
    children: List["TreeNode"] = []


class PageContentOut(BaseModel):
    path: str
    content: str
    locked_by: Optional[str] = None


class LockIn(BaseModel):
    path: str
    # 窗口级令牌：operator@windowId。缺省时退化为 operator（兼容旧客户端），
    # 同账号多窗口编辑同页会互斥；前端每标签页生成独立 windowId。
    holder: Optional[str] = None


class CommitIn(BaseModel):
    message: Optional[str] = None


class CommitOut(BaseModel):
    committed: bool
    commit: Optional[str] = None
    message: str
    files: List[str] = []
    date: Optional[datetime] = None


# ---- History ----

class HistoryEntry(BaseModel):
    commit: str
    author: str
    date: str
    message: str


class DiffOut(BaseModel):
    diff: str
    truncated: bool = False


class RevertIn(BaseModel):
    path: str
    commit: str


# ---- Explore ----

class SearchResult(BaseModel):
    path: str
    title: str
    kind: str  # title / body / tag
    snippet: str = ""
    tags: List[str] = []


class BacklinkOut(BaseModel):
    path: str
    title: str
    aliases: List[str] = []


class GraphNode(BaseModel):
    path: str
    title: str
    tags: List[str] = []


class GraphEdge(BaseModel):
    src: str
    dst: str
    type: str


class GraphOut(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class AttachmentOut(BaseModel):
    path: str  # 仓库内相对路径，如 attachments/xxx.png
    name: str
    size: int
