import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, not_found, locked as locked_exc, forbidden
from app.models.case.case_folder import CaseFolder
from app.models.case.case_map import CaseMap
from app.models.case.case_version import CaseVersion
from app.models.task.task import Task
from app.services.case.folder_service import get_folder_or_404, is_valid_oid
from app.utils.validators import sanitize_node


LOCK_TIMEOUT_MINUTES = 1


def _oid(oid: str) -> ObjectId:
    return ObjectId(oid)


async def get_map_or_404(map_id: str) -> CaseMap:
    if not is_valid_oid(map_id):
        raise not_found("map_not_found", "导图不存在")
    map_obj = await CaseMap.get(_oid(map_id))
    if map_obj is None or map_obj.is_deleted:
        raise not_found("map_not_found", "导图不存在")
    return map_obj


async def get_latest_version(map_id: str) -> Optional[CaseVersion]:
    versions = await CaseVersion.find(CaseVersion.map_id == map_id).sort(-CaseVersion.version_no).limit(1).to_list()
    return versions[0] if versions else None


async def get_latest_versions_for_maps(map_ids: List[str]) -> List[CaseVersion]:
    """批量获取每个 map_id 的最新版本（利用 version_no 降序取第一条）。"""
    if not map_ids:
        return []
    # 先取所有候选版本，再在内存按 version_no 分组取最大
    versions = await CaseVersion.find({"map_id": {"$in": map_ids}}).to_list()
    latest_by_map: Dict[str, CaseVersion] = {}
    for version in versions:
        existing = latest_by_map.get(version.map_id)
        if existing is None or version.version_no > existing.version_no:
            latest_by_map[version.map_id] = version
    return list(latest_by_map.values())


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_last_modified(map_obj: CaseMap, latest_version: Optional[CaseVersion] = None) -> datetime:
    if latest_version is None:
        latest_version = await get_latest_version(str(map_obj.id))
    last = _ensure_aware(map_obj.created_at)
    if latest_version:
        last = max(last, _ensure_aware(latest_version.created_at))
    if map_obj.locked_at:
        last = max(last, _ensure_aware(map_obj.locked_at))
    return last


def _build_default_root(title: str) -> Dict[str, Any]:
    return {
        "root": {
            "data": {
                "text": title,
                "uid": "root",
                "expand": True,
            },
            "children": [],
        },
        "layout": "logicalStructure",
        "theme": {"template": "default", "config": {}},
        "view": {"transform": {"scale": 1, "x": 0, "y": 0}},
    }


async def create_map(title: str, folder_id: Optional[str], root: Optional[Dict[str, Any]], owner: str) -> CaseMap:
    if folder_id:
        await get_folder_or_404(folder_id)

    map_obj = CaseMap(
        title=title,
        owner=owner,
        folder_id=folder_id,
        current_version=1,
    )
    await map_obj.insert()

    root_data = root if root else _build_default_root(title)
    root_data["root"] = sanitize_node(root_data["root"])

    version = CaseVersion(
        map_id=str(map_obj.id),
        version_no=1,
        root=root_data,
        changelog="初始版本",
        operator_id=owner,
    )
    await version.insert()
    return map_obj


async def get_map_detail(map_id: str) -> Dict[str, Any]:
    map_obj = await get_map_or_404(map_id)
    latest_version = await get_latest_version(map_id)

    # 检查锁是否超时
    locked_by = map_obj.locked_by
    locked_at = map_obj.locked_at
    if locked_by and locked_at:
        locked_at = _ensure_aware(locked_at)
        if datetime.now(timezone.utc) - locked_at > timedelta(minutes=LOCK_TIMEOUT_MINUTES):
            locked_by = None
            locked_at = None

    last_modified_at = _ensure_aware(map_obj.created_at)
    if latest_version:
        last_modified_at = max(last_modified_at, _ensure_aware(latest_version.created_at))
    if locked_at:
        last_modified_at = max(last_modified_at, _ensure_aware(locked_at))

    latest_root = None
    if latest_version and isinstance(getattr(latest_version, "root", None), dict):
        latest_root = latest_version.root

    return {
        "id": str(map_obj.id),
        "title": map_obj.title,
        "owner": map_obj.owner,
        "folder_id": map_obj.folder_id,
        "current_version": map_obj.current_version,
        "created_at": map_obj.created_at,
        "last_modified_at": last_modified_at,
        "temp_content": map_obj.temp_content,
        "latest_root": latest_root,
        "locked_by": locked_by,
        "locked_at": locked_at,
    }


async def update_map_draft(map_id: str, temp_content: Optional[Dict[str, Any]], title: Optional[str], operator: str) -> None:
    map_obj = await get_map_or_404(map_id)
    if title is not None:
        map_obj.title = title
    if temp_content is not None:
        map_obj.temp_content = temp_content
    if map_obj.locked_by == operator:
        map_obj.locked_at = datetime.now(timezone.utc)
    await map_obj.save()


async def delete_map(map_id: str) -> None:
    map_obj = await get_map_or_404(map_id)
    map_obj.is_deleted = True
    await map_obj.save()
    # 任务引用为软引用：导图删除后任务引用置 null，不级联删任务
    await Task.find(Task.case_map_id == map_id).update_many(
        {"$set": {"case_map_id": None, "case_node_id": None}}
    )


async def move_map(map_id: str, folder_id: Optional[str]) -> CaseMap:
    map_obj = await get_map_or_404(map_id)
    if folder_id:
        await get_folder_or_404(folder_id)
    map_obj.folder_id = folder_id
    await map_obj.save()
    return map_obj


async def _generate_unique_title(folder_id: Optional[str], base_title: str, exclude_id: Optional[str] = None) -> str:
    # 查询同文件夹下标题为 base_title 或 base_title(N) 的导图，避免全表加载
    regex = f"^{re.escape(base_title)}(\\(\\d+\\))?$"
    query = {
        "folder_id": folder_id,
        "is_deleted": False,
        "title": {"$regex": regex},
    }
    maps = await CaseMap.find(query).to_list()
    existing_titles = {m.title for m in maps if str(m.id) != exclude_id}

    if base_title not in existing_titles:
        return base_title

    counter = 1
    while True:
        candidate = f"{base_title}({counter})"
        if candidate not in existing_titles:
            return candidate
        counter += 1


async def copy_map(map_id: str, folder_id: Optional[str], operator: str) -> CaseMap:
    source = await get_map_or_404(map_id)
    target_folder_id = folder_id if folder_id is not None else source.folder_id

    latest_version = await get_latest_version(map_id)
    if latest_version is None:
        raise not_found("version_not_found", "源导图没有版本")

    new_title = await _generate_unique_title(target_folder_id, f"{source.title} 副本")

    new_map = CaseMap(
        title=new_title,
        owner=operator,
        folder_id=target_folder_id,
        current_version=1,
    )
    await new_map.insert()

    version = CaseVersion(
        map_id=str(new_map.id),
        version_no=1,
        root=latest_version.root,
        changelog=f"复制自 {source.title}",
        operator_id=operator,
    )
    await version.insert()
    return new_map


async def list_maps(folder_id: Optional[str], q: Optional[str], list_all: bool = False) -> List[CaseMap]:
    if q:
        regex = re.escape(q)
        maps = await CaseMap.find(
            {"title": {"$regex": regex, "$options": "i"}, "is_deleted": False}
        ).sort(-CaseMap.created_at).limit(50).to_list()
        return maps

    if list_all:
        maps = await CaseMap.find({"is_deleted": False}).sort(-CaseMap.created_at).to_list()
        return maps

    query = {"folder_id": folder_id, "is_deleted": False}
    maps = await CaseMap.find(query).sort(-CaseMap.created_at).to_list()
    return maps


async def acquire_lock(map_id: str, operator: str) -> CaseMap:
    map_obj = await get_map_or_404(map_id)
    now = datetime.now(timezone.utc)

    if map_obj.locked_by and map_obj.locked_by != operator:
        if map_obj.locked_at and now - map_obj.locked_at <= timedelta(minutes=LOCK_TIMEOUT_MINUTES):
            raise locked_exc(
                "map_locked",
                "导图已被他人锁定",
                {"locked_by": map_obj.locked_by, "locked_at": map_obj.locked_at.isoformat()},
            )

    map_obj.locked_by = operator
    map_obj.locked_at = now
    await map_obj.save()
    return map_obj


async def release_lock(map_id: str, operator: str, is_admin: bool = False) -> None:
    map_obj = await get_map_or_404(map_id)
    if map_obj.locked_by and map_obj.locked_by != operator and not is_admin:
        raise forbidden("只有锁定人或管理员可释放锁")
    map_obj.locked_by = None
    map_obj.locked_at = None
    await map_obj.save()
