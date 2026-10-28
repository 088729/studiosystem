from typing import List, Optional

from datetime import datetime, timezone

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.task.task import Task
from app.models.task.task_list import TaskList
from app.services.case.folder_service import is_valid_oid


async def get_list_or_404(list_id: str, owner: str) -> TaskList:
    if not is_valid_oid(list_id):
        raise not_found("list_not_found", "清单不存在")
    task_list = await TaskList.get(ObjectId(list_id))
    if task_list is None or task_list.owner != owner:
        raise not_found("list_not_found", "清单不存在")
    return task_list


async def list_lists(owner: str) -> List[TaskList]:
    return await TaskList.find(TaskList.owner == owner).sort("sort_order").to_list()


async def create_list(
    name: str,
    color: Optional[str],
    owner: str,
    group: Optional[str] = None,
    icon: Optional[str] = None,
    kind: str = "task",
) -> TaskList:
    if kind not in ("task", "note"):
        raise bad_request("invalid_kind", "清单类型须为 task 或 note")
    last = (
        await TaskList.find(TaskList.owner == owner)
        .sort("-sort_order")
        .limit(1)
        .to_list()
    )
    sort_order = (last[0].sort_order + 1) if last else 0
    task_list = TaskList(
        name=name,
        owner=owner,
        color=color or "#4f6ef7",
        icon=icon,
        group=group,
        kind=kind,
        sort_order=sort_order,
    )
    await task_list.insert()
    return task_list


async def update_list(list_id: str, data: dict, owner: str) -> TaskList:
    task_list = await get_list_or_404(list_id, owner)
    if data.get("kind") is not None and data["kind"] not in ("task", "note"):
        raise bad_request("invalid_kind", "清单类型须为 task 或 note")
    for key, value in data.items():
        setattr(task_list, key, value)
    await task_list.save()
    return task_list


async def delete_list(list_id: str, owner: str) -> None:
    task_list = await get_list_or_404(list_id, owner)
    # 其下任务落收集箱，不物理删除任务（看板分组一并清除）
    await Task.find(Task.list_id == list_id).update_many({"$set": {"list_id": None, "group": None}})
    await task_list.delete()


# ---------- 看板分组（对齐主流待办应用：清单内自定义分组列） ----------


async def add_group(list_id: str, name: str, owner: str, index: int | None = None) -> TaskList:
    task_list = await get_list_or_404(list_id, owner)
    name = name.strip()
    if not name:
        raise bad_request("group_name_empty", "分组名不能为空")
    if name in (task_list.board_groups or []):
        raise bad_request("group_name_conflict", "分组名已存在")
    groups = list(task_list.board_groups or [])
    if index is None:
        groups.append(name)
    else:
        groups.insert(max(0, min(index, len(groups))), name)
    task_list.board_groups = groups
    await task_list.save()
    return task_list


async def rename_group(list_id: str, from_name: str, to_name: str, owner: str) -> TaskList:
    task_list = await get_list_or_404(list_id, owner)
    groups = task_list.board_groups or []
    if from_name not in groups:
        raise not_found("group_not_found", "分组不存在")
    to_name = to_name.strip()
    if not to_name:
        raise bad_request("group_name_empty", "分组名不能为空")
    if to_name != from_name and to_name in groups:
        raise bad_request("group_name_conflict", "分组名已存在")
    task_list.board_groups = [to_name if g == from_name else g for g in groups]
    await task_list.save()
    # 级联改写清单内任务的看板分组
    if to_name != from_name:
        await Task.find(Task.list_id == list_id, Task.group == from_name).update_many(
            {"$set": {"group": to_name}}
        )
    return task_list


async def delete_group(list_id: str, name: str, owner: str) -> TaskList:
    task_list = await get_list_or_404(list_id, owner)
    groups = task_list.board_groups or []
    if name not in groups:
        raise not_found("group_not_found", "分组不存在")
    task_list.board_groups = [g for g in groups if g != name]
    await task_list.save()
    # 组内任务回落未分组列，不删任务
    await Task.find(Task.list_id == list_id, Task.group == name).update_many(
        {"$set": {"group": None}}
    )
    return task_list


async def move_group(
    owner: str,
    name: str,
    from_list_id: Optional[str],
    to_list_id: Optional[str],
) -> None:
    """分组「移动到」另一清单/收集箱（对齐主流待办应用）：分组名随迁，组内任务整体移动并保留分组。
    源/目标为收集箱时 list_id=null，分组存 TaskSettings.inbox_board_groups；目标已有同名分组则任务并入。"""
    from app.services.task.settings_service import get_settings

    if (from_list_id or None) == (to_list_id or None):
        raise bad_request("group_move_same", "目标清单与当前相同")

    async def _container(list_id):
        # 返回 (文档, 分组字段名, 分组名列表)
        if list_id is None:
            s = await get_settings(owner)
            return s, "inbox_board_groups", list(s.inbox_board_groups or [])
        lst = await get_list_or_404(list_id, owner)
        return lst, "board_groups", list(lst.board_groups or [])

    src_doc, src_field, src_groups = await _container(from_list_id)
    dst_doc, dst_field, dst_groups = await _container(to_list_id)
    if name not in src_groups:
        raise not_found("group_not_found", "分组不存在")
    src_groups.remove(name)
    if name not in dst_groups:
        dst_groups.append(name)

    # 组内任务整体迁移并保留分组（move_task 跨清单会清 group，故直接改库）；子任务随父迁移
    list_cond = Task.list_id == None if from_list_id is None else Task.list_id == from_list_id  # noqa: E711
    moved = await Task.find(Task.owner == owner, list_cond, Task.group == name).to_list()
    if moved:
        await Task.find({"_id": {"$in": [t.id for t in moved]}}).update_many(
            {"$set": {"list_id": to_list_id}}
        )
        await Task.find(Task.owner == owner, {"parent_id": {"$in": [str(t.id) for t in moved]}}).update_many(
            {"$set": {"list_id": to_list_id}}
        )

    setattr(src_doc, src_field, src_groups)
    setattr(dst_doc, dst_field, dst_groups)
    # 收集箱分组存 TaskSettings（带 updated_at），清单分组存 TaskList
    now = datetime.now(timezone.utc)
    if src_field == "inbox_board_groups":
        src_doc.updated_at = now
    if dst_field == "inbox_board_groups":
        dst_doc.updated_at = now
    await src_doc.save()
    await dst_doc.save()
