from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class FolderRename(BaseModel):
    name: str


class FolderMove(BaseModel):
    parent_id: Optional[str] = None


class FolderOut(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    depth: int
    owner: str
    created_at: datetime


class FolderTreeResponse(BaseModel):
    items: List[FolderOut]


class MapCreate(BaseModel):
    title: str
    folder_id: Optional[str] = None
    root: Optional[Dict[str, Any]] = None


class MapRename(BaseModel):
    title: str


class MapDraftUpdate(BaseModel):
    temp_content: Optional[Dict[str, Any]] = None
    title: Optional[str] = None


class MapMove(BaseModel):
    folder_id: Optional[str] = None


class MapCopy(BaseModel):
    folder_id: Optional[str] = None


class MapOut(BaseModel):
    id: str
    title: str
    owner: str
    folder_id: Optional[str]
    current_version: int
    created_at: datetime
    last_modified_at: Optional[datetime] = None


class MapDetailOut(MapOut):
    temp_content: Optional[Dict[str, Any]]
    latest_root: Optional[Dict[str, Any]]
    locked_by: Optional[str]
    locked_at: Optional[datetime]


class MapListResponse(BaseModel):
    items: List[MapOut]


class SnapshotRequest(BaseModel):
    root: Dict[str, Any]
    changelog: str = "系统自动保存"
    overwrite: bool = False


class RollbackRequest(BaseModel):
    version_no: int


class VersionOut(BaseModel):
    id: str
    map_id: str
    version_no: int
    changelog: str
    operator_id: str
    created_at: datetime


class VersionDetailOut(VersionOut):
    root: Dict[str, Any]


class VersionListResponse(BaseModel):
    items: List[VersionOut]
    total: int


class AssetOut(BaseModel):
    id: str
    map_id: str
    node_id: str
    url: str
    file_type: str
    file_size: int
    file_hash: str
    relative_path: str
    refer_count: int
    created_at: datetime


class AssetHashCheck(BaseModel):
    map_id: str
    file_hash: str


class AssetHashCheckResponse(BaseModel):
    exists: bool
    asset: Optional[AssetOut] = None
