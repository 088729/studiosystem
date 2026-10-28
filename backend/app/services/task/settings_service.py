from datetime import datetime, timezone

from app.core.exceptions import bad_request, not_found
from app.models.task.task import Task
from app.models.task.task_settings import TaskSettings

_DEFAULTS = {
    "default_list_id": None,
    "default_due": "none",
    "default_priority": 0,
    "default_reminder_minutes": None,
    "default_reminder_allday": "none",
    "default_range_minutes": 60,
    "default_tags": [],
}


async def get_settings(owner: str) -> TaskSettings:
    """无记录时按默认值落库一条，保证后续 upsert 语义。"""
    s = await TaskSettings.find_one(TaskSettings.owner == owner)
    if s is None:
        s = TaskSettings(owner=owner, **_DEFAULTS)
        await s.insert()
    return s


async def save_settings(owner: str, data: dict) -> TaskSettings:
    s = await get_settings(owner)
    for k, v in data.items():
        setattr(s, k, v)
    s.updated_at = datetime.now(timezone.utc)
    await s.save()
    return s


# ---------- 收集箱自定义分组（对齐主流待办应用：收集箱支持分组；list_id=null 任务的 group 须属其中） ----------


async def add_inbox_group(owner: str, name: str, index: int | None = None) -> TaskSettings:
    s = await get_settings(owner)
    name = name.strip()
    if not name:
        raise bad_request("group_name_empty", "分组名不能为空")
    if name in (s.inbox_board_groups or []):
        raise bad_request("group_name_conflict", "分组名已存在")
    groups = list(s.inbox_board_groups or [])
    if index is None:
        groups.append(name)
    else:
        groups.insert(max(0, min(index, len(groups))), name)
    s.inbox_board_groups = groups
    s.updated_at = datetime.now(timezone.utc)
    await s.save()
    return s


async def rename_inbox_group(owner: str, from_name: str, to_name: str) -> TaskSettings:
    s = await get_settings(owner)
    groups = list(s.inbox_board_groups or [])
    if from_name not in groups:
        raise not_found("group_not_found", "分组不存在")
    to_name = to_name.strip()
    if not to_name:
        raise bad_request("group_name_empty", "分组名不能为空")
    if to_name != from_name and to_name in groups:
        raise bad_request("group_name_conflict", "分组名已存在")
    s.inbox_board_groups = [to_name if g == from_name else g for g in groups]
    s.updated_at = datetime.now(timezone.utc)
    await s.save()
    # 级联改写收集箱任务的分组
    if to_name != from_name:
        await Task.find(Task.owner == owner, Task.list_id == None, Task.group == from_name).update_many(  # noqa: E711
            {"$set": {"group": to_name}}
        )
    return s


async def delete_inbox_group(owner: str, name: str) -> TaskSettings:
    s = await get_settings(owner)
    groups = list(s.inbox_board_groups or [])
    if name not in groups:
        raise not_found("group_not_found", "分组不存在")
    s.inbox_board_groups = [g for g in groups if g != name]
    s.updated_at = datetime.now(timezone.utc)
    await s.save()
    # 组内收集箱任务回落未分组，不删任务
    await Task.find(Task.owner == owner, Task.list_id == None, Task.group == name).update_many(  # noqa: E711
        {"$set": {"group": None}}
    )
    return s
