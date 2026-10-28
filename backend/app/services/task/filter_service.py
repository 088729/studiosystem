import re
from datetime import datetime
from typing import List, Tuple

from bson import ObjectId

from app.core.exceptions import not_found
from app.models.task.task import Task
from app.models.task.task_filter import TaskFilter
from app.services.case.folder_service import is_valid_oid


async def get_filter_or_404(filter_id: str, owner: str) -> TaskFilter:
    if not is_valid_oid(filter_id):
        raise not_found("filter_not_found", "筛选器不存在")
    f = await TaskFilter.get(ObjectId(filter_id))
    if f is None or f.owner != owner:
        raise not_found("filter_not_found", "筛选器不存在")
    return f


async def list_filters(owner: str) -> List[TaskFilter]:
    return await TaskFilter.find(TaskFilter.owner == owner).sort("sort_order").to_list()


async def create_filter(owner: str, data) -> TaskFilter:
    f = TaskFilter(owner=owner, **data.model_dump())
    await f.insert()
    return f


async def update_filter(filter_id: str, owner: str, data: dict) -> TaskFilter:
    f = await get_filter_or_404(filter_id, owner)
    for key, value in data.items():
        setattr(f, key, value)
    await f.save()
    return f


async def delete_filter(filter_id: str, owner: str) -> None:
    f = await get_filter_or_404(filter_id, owner)
    await f.delete()


async def count_filter_tasks(f: TaskFilter, owner: str, bounds: Tuple[datetime, datetime, datetime, datetime]) -> int:
    """筛选器命中任务数（侧栏过滤器行计数徽标，口径与 list_tasks 一致：过滤软删与子任务）。"""
    conditions = [
        Task.is_deleted == False,  # noqa: E712
        Task.parent_id == None,  # noqa: E711
        *build_filter_query(f, owner, bounds),
    ]
    return await Task.find(*conditions).count()


def build_filter_query(
    f: TaskFilter,
    owner: str,
    bounds: Tuple[datetime, datetime, datetime, datetime],
) -> List:
    """把 TaskFilter 翻译成 Mongo 查询条件（owner 隔离，复用 list_tasks 的过滤语义）。

    bounds = (today_start, tomorrow_start, day_after, next7)，与 list_tasks 口径一致。
    """
    today_start, tomorrow_start, _, next7 = bounds
    conditions = [Task.owner == owner]
    if f.lists:
        conditions.append({"list_id": {"$in": f.lists}})
    if f.tags:
        conditions.append({"tags": {"$in": f.tags}})
    if f.priorities:
        conditions.append({"priority": {"$in": f.priorities}})
    if f.status != "any":
        conditions.append(Task.status == f.status)
    if f.keyword:
        conditions.append({"title": {"$regex": f".*{re.escape(f.keyword)}.*", "$options": "i"}})
    if f.due_range == "overdue":
        conditions += [Task.status == "todo", Task.due_at != None, Task.due_at < today_start]  # noqa: E711
    elif f.due_range == "today":
        conditions += [Task.status == "todo", Task.due_at != None, Task.due_at < tomorrow_start]  # noqa: E711
    elif f.due_range == "next7":
        conditions += [Task.status == "todo", Task.due_at != None, Task.due_at < next7]  # noqa: E711
    elif f.due_range == "no_date":
        conditions.append(Task.due_at == None)  # noqa: E711
    return conditions
