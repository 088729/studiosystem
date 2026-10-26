from collections import deque
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.case.case_folder import CaseFolder
from app.models.case.case_map import CaseMap


MAX_FOLDER_DEPTH = 2


def is_valid_oid(oid: str) -> bool:
    try:
        ObjectId(oid)
        return True
    except Exception:
        return False


async def get_folder_or_404(folder_id: str) -> CaseFolder:
    if not is_valid_oid(folder_id):
        raise not_found("folder_not_found", "文件夹不存在")
    folder = await CaseFolder.get(ObjectId(folder_id))
    if folder is None:
        raise not_found("folder_not_found", "文件夹不存在")
    return folder


async def create_folder(name: str, parent_id: Optional[str], owner: str) -> CaseFolder:
    depth = 0
    if parent_id:
        parent = await get_folder_or_404(parent_id)
        depth = parent.depth + 1
    if depth > MAX_FOLDER_DEPTH:
        raise bad_request("folder_depth_exceeded", "文件夹层级不能超过三层")

    folder = CaseFolder(
        name=name,
        parent_id=parent_id,
        depth=depth,
        owner=owner,
    )
    await folder.insert()
    return folder


async def rename_folder(folder_id: str, name: str) -> CaseFolder:
    folder = await get_folder_or_404(folder_id)
    folder.name = name
    await folder.save()
    return folder


async def move_folder(folder_id: str, new_parent_id: Optional[str]) -> CaseFolder:
    folder = await get_folder_or_404(folder_id)

    if new_parent_id == folder_id:
        raise bad_request("invalid_move", "不能移动到自身")

    new_depth = 0
    if new_parent_id:
        parent = await get_folder_or_404(new_parent_id)
        new_depth = parent.depth + 1
        # 防止循环：检查新父级是否是当前文件夹的子孙
        current = parent
        while current.parent_id:
            if current.parent_id == folder_id:
                raise bad_request("invalid_move", "不能移动到自身或子孙文件夹")
            current = await CaseFolder.get(ObjectId(current.parent_id))
            if current is None:
                break

    if new_depth > MAX_FOLDER_DEPTH:
        raise bad_request("folder_depth_exceeded", "目标位置超过最大层级")

    delta = new_depth - folder.depth
    folder.parent_id = new_parent_id
    folder.depth = new_depth
    await folder.save()

    # BFS 更新所有子孙的 depth
    queue = deque([folder_id])
    while queue:
        current_id = queue.popleft()
        children = await CaseFolder.find(CaseFolder.parent_id == current_id).to_list()
        for child in children:
            child.depth += delta
            await child.save()
            queue.append(str(child.id))

    return folder


async def delete_folder(folder_id: str) -> None:
    folder = await get_folder_or_404(folder_id)

    # BFS 收集所有子孙文件夹 ID
    folder_ids = {folder_id}
    queue = deque([folder_id])
    while queue:
        current_id = queue.popleft()
        children = await CaseFolder.find(CaseFolder.parent_id == current_id).to_list()
        for child in children:
            child_id = str(child.id)
            folder_ids.add(child_id)
            queue.append(child_id)

    # 软删除这些文件夹下的所有导图
    await CaseMap.find({"folder_id": {"$in": list(folder_ids)}}).update(
        {"$set": {"is_deleted": True}}
    )

    # 物理删除文件夹
    await CaseFolder.find({"_id": {"$in": [ObjectId(fid) for fid in folder_ids]}}).delete()


async def list_folders() -> List[CaseFolder]:
    return await CaseFolder.find_all().to_list()
