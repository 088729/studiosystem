"""清单共享与可见性。

规则：
- 清单可见 = owner == me 或 me ∈ members
- 任务可见 = owner == me 或任务属于我可访问的共享清单
- 任务可写 = 任务创建者，或所属共享清单的 editor 成员（viewer 只读）
- 收集箱任务（list_id=null）永远仅 owner 可见
- 智能清单/日历/summary 仍只含 owner == me（在 task_service 中保持）
- 存量兼容：旧 members 为 List[str]，查询同时匹配字符串与嵌入文档两种形态
"""
from typing import List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.task.task import Task
from app.models.task.task_list import Member, TaskList
from app.models.user import User
from app.services.case.folder_service import is_valid_oid

MEMBER_ROLES = ("viewer", "editor")


def member_role(task_list: TaskList, username: str) -> Optional[str]:
    """用户在清单中的角色；非成员返回 None。旧 str 成员兜底视为 viewer。"""
    for m in task_list.members or []:
        name = m.username if isinstance(m, Member) else m
        if name == username:
            return m.role if isinstance(m, Member) else "viewer"
    return None


async def get_accessible_list_ids(user: str) -> List[str]:
    """我作为成员可访问的共享清单 id 列表。"""
    lists = await TaskList.find({"$or": [{"members": user}, {"members.username": user}]}).to_list()
    return [str(l.id) for l in lists]


def is_list_accessible(task_list: TaskList, user: str) -> bool:
    return task_list.owner == user or member_role(task_list, user) is not None


async def get_accessible_list_or_404(list_id: str, user: str) -> TaskList:
    """清单存在且对我可见（owner 或成员），否则 404。"""
    if not is_valid_oid(list_id):
        raise not_found("list_not_found", "清单不存在")
    task_list = await TaskList.get(ObjectId(list_id))
    if task_list is None or not is_list_accessible(task_list, user):
        raise not_found("list_not_found", "清单不存在")
    return task_list


async def can_access_task(task: Task, user: str) -> bool:
    if task.owner == user:
        return True
    if not task.list_id or not is_valid_oid(task.list_id):
        return False
    task_list = await TaskList.get(ObjectId(task.list_id))
    return task_list is not None and is_list_accessible(task_list, user)


async def can_edit_task(task: Task, user: str) -> bool:
    """任务写权限：任务创建者，或所属共享清单的 editor 成员。"""
    if task.owner == user:
        return True
    if not task.list_id or not is_valid_oid(task.list_id):
        return False
    task_list = await TaskList.get(ObjectId(task.list_id))
    return task_list is not None and member_role(task_list, user) == "editor"


async def list_shared_lists(user: str) -> List[TaskList]:
    return (
        await TaskList.find({"$or": [{"members": user}, {"members.username": user}]})
        .sort("sort_order")
        .to_list()
    )


async def add_member(list_id: str, username: str, owner: str, role: str = "viewer") -> TaskList:
    if role not in MEMBER_ROLES:
        raise bad_request("invalid_role", "角色仅支持 viewer / editor")
    task_list = await _get_owned_list_or_404(list_id, owner)
    if username == owner:
        raise bad_request("invalid_member", "清单所有者无需添加为成员")
    user = await User.find_one(User.username == username, User.is_active == True)  # noqa: E712
    if user is None:
        raise bad_request("user_not_found", "用户不存在或已禁用")
    if member_role(task_list, username) is None:
        members = task_list.members or []
        members.append(Member(username=username, role=role))
        task_list.members = members
        await task_list.save()
    return task_list


async def remove_member(list_id: str, username: str, owner: str) -> TaskList:
    task_list = await _get_owned_list_or_404(list_id, owner)
    if member_role(task_list, username) is not None:
        task_list.members = [
            m for m in (task_list.members or [])
            if (m.username if isinstance(m, Member) else m) != username
        ]
        await task_list.save()
    return task_list


async def set_member_role(list_id: str, username: str, role: str, owner: str) -> TaskList:
    """修改成员角色（仅清单所有者）。"""
    if role not in MEMBER_ROLES:
        raise bad_request("invalid_role", "角色仅支持 viewer / editor")
    task_list = await _get_owned_list_or_404(list_id, owner)
    for m in task_list.members or []:
        if isinstance(m, Member) and m.username == username:
            m.role = role
            await task_list.save()
            return task_list
    raise not_found("member_not_found", "成员不存在")


async def leave_list(list_id: str, username: str) -> dict:
    """成员自助退出共享；所有者不能退出（可转让所有权）。"""
    task_list = await get_accessible_list_or_404(list_id, username)
    if task_list.owner == username:
        raise bad_request("owner_cannot_leave", "清单所有者不能退出，可转让所有权后再退出")
    task_list.members = [
        m for m in (task_list.members or [])
        if (m.username if isinstance(m, Member) else m) != username
    ]
    await task_list.save()
    return {"ok": True}


async def transfer_owner(list_id: str, to: str, owner: str) -> TaskList:
    """转移所有权：接收者须为成员；原 owner 降为 editor。"""
    task_list = await _get_owned_list_or_404(list_id, owner)
    if member_role(task_list, to) is None:
        raise bad_request("not_member", "接收者不是成员")
    members = [
        m for m in (task_list.members or [])
        if (m.username if isinstance(m, Member) else m) != to
    ]
    members.append(Member(username=owner, role="editor"))
    task_list.members = members
    task_list.owner = to
    await task_list.save()
    return task_list


async def list_active_users() -> List[User]:
    """成员选择数据源：全部活跃用户。"""
    return await User.find(User.is_active == True).to_list()  # noqa: E712


async def _get_owned_list_or_404(list_id: str, owner: str) -> TaskList:
    if not is_valid_oid(list_id):
        raise not_found("list_not_found", "清单不存在")
    task_list = await TaskList.get(ObjectId(list_id))
    if task_list is None:
        raise not_found("list_not_found", "清单不存在")
    if task_list.owner != owner:
        raise forbidden("仅清单所有者可管理共享成员")
    return task_list


async def get_task_or_none(task_id: str) -> Optional[Task]:
    if not is_valid_oid(task_id):
        return None
    return await Task.get(ObjectId(task_id))
