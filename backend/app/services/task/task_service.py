import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from beanie.operators import In
from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.case.case_map import CaseMap
from app.models.case.case_version import CaseVersion
from app.models.task.comment import TaskComment
from app.models.task.task import Attachment, Reminder, Task
from app.models.task.task_list import TaskList
from app.models.user import User
from app.services.case.folder_service import is_valid_oid
from app.services.task import filter_service, settings_service, share_service
from app.services.task.list_service import get_list_or_404
from app.services.task.recurrence import next_due, should_stop

SORT_STEP = 1024  # sort_order 稀疏步长

# 任务附件：类型/大小约束（对齐评论图片）
ALLOWED_ATTACHMENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB


async def get_task_or_404(task_id: str, owner: str, write: bool = False) -> Task:
    """读取：owner 或共享清单成员可见；写入（write=True）：任务创建者或清单 editor 成员。"""
    if not is_valid_oid(task_id):
        raise not_found("task_not_found", "任务不存在")
    task = await Task.get(ObjectId(task_id))
    if task is None or task.is_deleted:
        raise not_found("task_not_found", "任务不存在")
    if task.owner == owner:
        return task
    if write:
        if await share_service.can_edit_task(task, owner):
            return task
        raise not_found("task_not_found", "任务不存在")
    if not await share_service.can_access_task(task, owner):
        raise not_found("task_not_found", "任务不存在")
    return task


def _day_bounds_utc(tz_offset_minutes: int) -> Tuple[datetime, datetime, datetime, datetime]:
    """按客户端时区偏移（本地 - UTC 的分钟数，东八区 +480）计算今日/明日/后日/+7天 00:00 的 UTC 边界。"""
    local_now = datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)
    local_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = local_today - timedelta(minutes=tz_offset_minutes)
    return (
        today_start,
        today_start + timedelta(days=1),
        today_start + timedelta(days=2),
        today_start + timedelta(days=7),
    )


async def list_tasks(
    owner: str,
    list_id: Optional[str] = None,
    smart: Optional[str] = None,
    filter_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    tz_offset_minutes: int = 0,
    limit: int = 200,
    offset: int = 0,
) -> List[Task]:
    if list_id and smart:
        raise bad_request("list_smart_conflict", "list_id 与 smart 互斥，只能传一个")
    if filter_id and (list_id or smart):
        raise bad_request("filter_conflict", "filter_id 与 list_id/smart 互斥，只能传一个")

    # 回收站：仅自己的已软删顶层任务，按删除时间倒序（不走公共 is_deleted=False 过滤）
    if smart == "trash":
        return await (
            Task.find(
                Task.owner == owner,
                Task.is_deleted == True,  # noqa: E712
                Task.parent_id == None,  # noqa: E711 子任务随父任务展示
            )
            .sort("-updated_at")
            .skip(offset)
            .limit(limit)
            .to_list()
        )

    conditions = [
        Task.is_deleted == False,  # noqa: E712
        Task.parent_id == None,  # noqa: E711 子任务不进列表，随父任务展示
    ]
    sort_field: List = ["sort_order"]

    today_start, tomorrow_start, day_after, next7 = _day_bounds_utc(tz_offset_minutes)

    if list_id:
        # 清单对我可见（owner 或共享成员）即可查其下全部任务
        await share_service.get_accessible_list_or_404(list_id, owner)
        conditions.append(Task.list_id == list_id)
    elif filter_id:
        # 保存的筛选器：翻译成查询条件（owner 隔离）
        f = await filter_service.get_filter_or_404(filter_id, owner)
        conditions += filter_service.build_filter_query(
            f, owner, (today_start, tomorrow_start, day_after, next7)
        )
    else:
        # 智能清单只含自己的任务（owner 隔离）
        conditions.append(Task.owner == owner)
        smart = smart or "all"
        if smart == "inbox":
            conditions.append(Task.list_id == None)  # noqa: E711
        elif smart == "today":  # todo 含逾期；done 仅含今日到期的（供「已完成」分组展示）
            conditions += [
                Task.due_at != None,  # noqa: E711
                Task.due_at < tomorrow_start,
                {"$or": [{"status": "todo"}, {"status": "done", "due_at": {"$gte": today_start}}]},
            ]
            sort_field = ["due_at"]
        elif smart == "tomorrow":
            conditions += [Task.due_at >= tomorrow_start, Task.due_at < day_after]
            sort_field = ["due_at"]
        elif smart == "next7":  # todo 含逾期；done 仅含今日起到期的
            conditions += [
                Task.due_at != None,  # noqa: E711
                Task.due_at < next7,
                {"$or": [{"status": "todo"}, {"status": "done", "due_at": {"$gte": today_start}}]},
            ]
            sort_field = ["due_at"]
        elif smart == "completed":
            conditions.append(Task.status == "done")
            sort_field = ["-completed_at"]
        elif smart == "all":
            sort_field = ["-created_at"]
        else:
            raise bad_request("invalid_smart", f"未知智能清单: {smart}")

    if status:
        conditions.append(Task.status == status)
    if priority is not None:
        conditions.append(Task.priority == priority)
    if tag:
        conditions.append(Task.tags == tag)
    if q:
        regex = {"$regex": f".*{re.escape(q)}.*", "$options": "i"}
        conditions.append({"$or": [{"title": regex}, {"note": regex}]})

    return (
        await Task.find(*conditions)
        .sort(*sort_field)
        .skip(offset)
        .limit(limit)
        .to_list()
    )


async def _next_sort_order(list_id: Optional[str], parent_id: Optional[str] = None) -> int:
    conditions = [Task.is_deleted == False, Task.parent_id == parent_id]  # noqa: E712
    if parent_id is None:
        conditions.append(Task.list_id == list_id if list_id else Task.list_id == None)  # noqa: E711
    last = await Task.find(*conditions).sort("-sort_order").limit(1).to_list()
    return (last[0].sort_order + SORT_STEP) if last else SORT_STEP


async def create_task(owner: str, data) -> Task:
    list_id = data.list_id
    if data.parent_id:
        parent = await get_task_or_404(data.parent_id, owner)
        if parent.parent_id is not None:
            raise bad_request("subtask_nesting", "只允许一级子任务")
        list_id = parent.list_id  # 子任务 list_id 始终与父任务一致
    elif list_id:
        # 清单对我可见（含共享成员）即可在其中建任务，任务 owner=当前用户
        await share_service.get_accessible_list_or_404(list_id, owner)

    # 看板分组校验：清单任务须属目标清单的 board_groups；收集箱任务须属本人的 inbox_board_groups
    if data.group:
        if not list_id:
            st = await settings_service.get_settings(owner)
            if data.group not in (st.inbox_board_groups or []):
                raise bad_request("group_invalid", "看板分组不存在")
        else:
            tl = await share_service.get_accessible_list_or_404(list_id, owner)
            if data.group not in (tl.board_groups or []):
                raise bad_request("group_invalid", "看板分组不存在")

    if data.case_map_id:
        if not is_valid_oid(data.case_map_id):
            raise not_found("map_not_found", "关联导图不存在")
        case_map = await CaseMap.get(ObjectId(data.case_map_id))
        if case_map is None or case_map.is_deleted:
            raise not_found("map_not_found", "关联导图不存在")

    if data.assignee:
        assignee = await User.find_one(User.username == data.assignee)
        if assignee is None:
            raise bad_request("assignee_not_found", "负责人不存在")

    # 笔记标记：显式传入优先，缺省跟随所属清单 kind（收集箱/子任务=普通任务，对齐主流待办应用笔记清单）
    explicit_note = getattr(data, "is_note", None)
    is_note = bool(explicit_note)
    if explicit_note is None and not data.parent_id and list_id:
        tl = await share_service.get_accessible_list_or_404(list_id, owner)
        is_note = tl.kind == "note"

    task = Task(
        title=data.title,
        note=data.note,
        list_id=list_id,
        parent_id=data.parent_id,
        group=data.group if not data.parent_id else None,
        owner=owner,
        assignee=data.assignee,
        priority=data.priority,
        tags=data.tags,
        due_at=data.due_at,
        all_day=data.all_day,
        start_at=data.start_at,
        duration_minutes=data.duration_minutes,
        reminders=data.reminders,
        persistent_reminder=data.persistent_reminder,
        recurrence=data.recurrence,
        case_map_id=data.case_map_id,
        case_node_id=data.case_node_id,
        is_pinned=getattr(data, 'is_pinned', False) if not data.parent_id else False,
        is_note=is_note if not data.parent_id else False,
        sort_order=await _next_sort_order(list_id, data.parent_id),
    )
    await task.insert()
    return task


async def update_task(task_id: str, data: dict, owner: str) -> Task:
    task = await get_task_or_404(task_id, owner, write=True)
    # list_id 走 move 接口，不允许在此变更
    data.pop("list_id", None)
    # 拖动转子任务（对齐主流待办应用：拖到另一任务右下方）：parent_id 单独校验处理
    if "parent_id" in data:
        new_parent = data.pop("parent_id")
        if new_parent:
            if new_parent == str(task.id):
                raise bad_request("subtask_self", "不能将任务转为自己的子任务")
            parent = await get_task_or_404(new_parent, owner)
            if parent.parent_id is not None:
                raise bad_request("subtask_nesting", "只允许一级子任务")
            has_children = await Task.find(
                Task.parent_id == str(task.id), Task.is_deleted == False  # noqa: E712
            ).limit(1).to_list()
            if has_children:
                raise bad_request("subtask_has_children", "该任务含子任务，请先处理其子任务")
            task.parent_id = new_parent
            task.list_id = parent.list_id  # 子任务 list_id 始终与父任务一致
            task.sort_order = await _next_sort_order(parent.list_id, new_parent)  # 落到子任务末尾
        elif task.parent_id is not None:
            # 显式传 null：转回普通任务，落到原清单末尾
            task.sort_order = await _next_sort_order(task.list_id, None)
            task.parent_id = None
    if data.get("assignee"):
        assignee = await User.find_one(User.username == data["assignee"])
        if assignee is None:
            raise bad_request("assignee_not_found", "负责人不存在")
    # 任务 → 笔记：含子任务不可转换（对齐主流待办应用）
    if data.get("is_note") is True and not task.is_note:
        has_children = await Task.find(
            Task.parent_id == str(task.id), Task.is_deleted == False  # noqa: E712
        ).limit(1).to_list()
        if has_children:
            raise bad_request("note_has_subtasks", "含子任务的任务无法转换为笔记")
    # 看板分组校验（看板拖拽换列）：清单任务须属所在清单的 board_groups；收集箱任务须属本人的 inbox_board_groups
    if "group" in data:
        new_group = data["group"]
        if new_group:
            if not task.list_id:
                st = await settings_service.get_settings(owner)
                if new_group not in (st.inbox_board_groups or []):
                    raise bad_request("group_invalid", "看板分组不存在")
            else:
                tl = await share_service.get_accessible_list_or_404(task.list_id, owner)
                if new_group not in (tl.board_groups or []):
                    raise bad_request("group_invalid", "看板分组不存在")
        elif task.parent_id is not None:
            # 子任务不入看板列，group 恒为 null，允许幂等置空
            data["group"] = None
    for key, value in data.items():
        # reminders 经 model_dump(exclude_unset=True) 后缺省字段（triggered/notified）被剥掉，
        # 裸 dict 落库会缺字段导致 reminder_loop 查询匹配不到，这里重建 Reminder 补全默认值
        if key == "reminders" and value is not None:
            value = [r if isinstance(r, Reminder) else Reminder(**r) for r in value]
        setattr(task, key, value)
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task


async def soft_delete_task(task_id: str, owner: str) -> None:
    task = await get_task_or_404(task_id, owner, write=True)
    now = datetime.now(timezone.utc)
    task.is_deleted = True
    task.updated_at = now
    await task.save()
    # 级联软删子任务
    await Task.find(Task.parent_id == task_id, Task.is_deleted == False).update_many(  # noqa: E712
        {"$set": {"is_deleted": True, "updated_at": now}}
    )


async def _get_deleted_task_or_404(task_id: str, owner: str) -> Task:
    """回收站操作（恢复/彻底删除）：仅任务创建者可操作自己的已软删任务。"""
    if not is_valid_oid(task_id):
        raise not_found("task_not_found", "任务不存在")
    task = await Task.get(ObjectId(task_id))
    if task is None or not task.is_deleted or task.owner != owner:
        raise not_found("task_not_found", "任务不存在")
    return task


async def restore_task(task_id: str, owner: str) -> Task:
    """恢复软删任务（级联恢复子任务）；原清单已删则落收集箱。"""
    task = await _get_deleted_task_or_404(task_id, owner)
    if task.list_id and (
        not is_valid_oid(task.list_id)
        or await TaskList.get(ObjectId(task.list_id)) is None
    ):
        task.list_id = None
    now = datetime.now(timezone.utc)
    task.is_deleted = False
    task.updated_at = now
    await task.save()
    # 级联恢复子任务
    await Task.find(Task.parent_id == task_id, Task.is_deleted == True).update_many(  # noqa: E712
        {"$set": {"is_deleted": False, "updated_at": now}}
    )
    return task


async def purge_task(task_id: str, owner: str) -> None:
    """彻底物理删除（含子任务与评论）。"""
    task = await _get_deleted_task_or_404(task_id, owner)
    sub_ids = [str(s.id) for s in await Task.find(Task.parent_id == task_id).to_list()]
    await Task.find(Task.parent_id == task_id).delete()
    await TaskComment.find(In(TaskComment.task_id, [task_id] + sub_ids)).delete()
    await task.delete()


async def complete_task(task_id: str, done: bool, owner: str) -> Task:
    # B2：共享清单任务收紧权限——viewer 不可完成/取消完成，仅 owner 或 editor
    task = await get_task_or_404(task_id, owner, write=True)
    target = "done" if done else "todo"
    if task.status == target:
        return task  # 幂等：状态已一致，不改写 completed_at、不重算 recurrence

    now = datetime.now(timezone.utc)
    task.status = target
    task.completed_at = now if done else None
    task.updated_at = now

    # 完成时清空已触发提醒，避免完成后仍弹提示（B3）
    if done:
        for reminder in task.reminders or []:
            reminder.triggered = False
            reminder.notified = False

    # 重复任务：完成时按规则生成下一实例（重置当前文档，不新增）
    if done and task.recurrence and task.due_at:
        rule = task.recurrence
        rule.occurrences_completed += 1
        due_at = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        next_at = next_due(rule, due_at)
        if not should_stop(rule, next_at):
            task.status = "todo"
            task.completed_at = None
            task.due_at = next_at
            for reminder in task.reminders:
                reminder.triggered = False
                reminder.notified = False
            # 子任务一并复位
            await Task.find(Task.parent_id == task_id, Task.is_deleted == False).update_many(  # noqa: E712
                {"$set": {"status": "todo", "completed_at": None, "updated_at": now}}
            )

    await task.save()
    return task


async def skip_task(task_id: str, owner: str) -> Task:
    """跳过本次：推进到下一次 due_at，不记完成次数。"""
    task = await get_task_or_404(task_id, owner, write=True)
    if not task.recurrence or not task.due_at:
        raise bad_request("skip_invalid", "该任务无重复规则或截止时间")

    rule = task.recurrence
    due_at = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
    next_at = next_due(rule, due_at)

    if next_at is None or should_stop(rule, next_at):
        task.recurrence = None  # 到结束条件：清空重复，保持 todo
    else:
        task.due_at = next_at
        for r in task.reminders or []:
            r.triggered = False
            r.notified = False
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task


async def move_task(task_id: str, list_id: Optional[str], owner: str) -> Task:
    task = await get_task_or_404(task_id, owner, write=True)
    if task.parent_id is not None:
        raise bad_request("subtask_move", "子任务随父任务移动，不能单独移动")
    if list_id:
        await share_service.get_accessible_list_or_404(list_id, owner)
    task.list_id = list_id
    task.group = None  # 跨清单移动后原看板分组失效，落目标清单未分组列
    task.sort_order = await _next_sort_order(list_id)
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    # 子任务 list_id 级联同步
    await Task.find(Task.parent_id == task_id, Task.is_deleted == False).update_many(  # noqa: E712
        {"$set": {"list_id": list_id}}
    )
    return task


async def batch_task(owner: str, ids: List[str], action: str, payload: dict) -> dict:
    """逐条执行批量操作（complete/delete/move/priority/due），权限校验与单任务接口一致，返回成功/失败明细。"""
    ok = 0
    failed = []
    for tid in ids:
        try:
            if action == "complete":
                await complete_task(tid, payload.get("done", True), owner)
            elif action == "delete":
                await soft_delete_task(tid, owner)
            elif action == "move":
                await move_task(tid, payload.get("list_id"), owner)
            elif action == "priority":
                task = await get_task_or_404(tid, owner, write=True)
                task.priority = payload.get("priority", 0)
                task.updated_at = datetime.now(timezone.utc)
                await task.save()
            elif action == "due":
                task = await get_task_or_404(tid, owner, write=True)
                due_at = payload.get("due_at")
                task.due_at = datetime.fromisoformat(due_at) if isinstance(due_at, str) else due_at
                if "all_day" in payload:
                    task.all_day = bool(payload["all_day"])
                # 批量「日期与提醒」：payload 带非空 reminders 时整体替换（含持续提醒标记）；
                # 清除日期时对齐单任务「清除」语义，一并清提醒/重复
                rems = payload.get("reminders")
                if rems:
                    task.reminders = [r if isinstance(r, Reminder) else Reminder(**r) for r in rems]
                    task.persistent_reminder = bool(payload.get("persistent_reminder", False))
                elif due_at is None:
                    task.reminders = []
                    task.persistent_reminder = False
                    task.recurrence = None
                task.updated_at = datetime.now(timezone.utc)
                await task.save()
            elif action == "tags":
                # 批量加标签（并集，不移除已有标签）
                task = await get_task_or_404(tid, owner, write=True)
                add = payload.get("tags") or []
                merged = list(dict.fromkeys([*(task.tags or []), *add]))
                if merged != (task.tags or []):
                    task.tags = merged
                    task.updated_at = datetime.now(timezone.utc)
                    await task.save()
            elif action == "pin":
                task = await get_task_or_404(tid, owner, write=True)
                task.is_pinned = bool(payload.get("pinned", True))
                task.updated_at = datetime.now(timezone.utc)
                await task.save()
            else:
                raise bad_request("invalid_batch_action", f"未知批量操作: {action}")
            ok += 1
        except Exception as e:  # noqa: BLE001 逐条容错：单条失败不影响其余
            failed.append({"id": tid, "reason": str(e)})
    return {"ok": ok, "failed": failed}


async def sort_task(
    task_id: str,
    owner: str,
    sort_order: Optional[int],
    before_task_id: Optional[str],
    after_task_id: Optional[str] = None,
) -> Task:
    task = await get_task_or_404(task_id, owner, write=True)
    if sort_order is None and before_task_id is None and after_task_id is None:
        raise bad_request("invalid_sort", "sort_order 与 before_task_id/after_task_id 至少传一个")

    if sort_order is not None:
        task.sort_order = sort_order
        task.updated_at = datetime.now(timezone.utc)
        await task.save()
        return task

    # 相对插入：取同层级兄弟（排除自身）
    conditions = [
        Task.is_deleted == False,  # noqa: E712
        Task.parent_id == task.parent_id,
        Task.id != task.id,
    ]
    if task.parent_id is None:
        conditions.append(Task.list_id == task.list_id if task.list_id else Task.list_id == None)  # noqa: E711
    siblings = await Task.find(*conditions).sort("sort_order").to_list()

    if before_task_id is not None:
        idx = next((i for i, s in enumerate(siblings) if str(s.id) == before_task_id), None)
        insert_idx = idx
    else:  # after_task_id：落到目标之后（含落尾，由后端算 sort_order，避免前端硬编码步长冲突，B4）
        idx = next((i for i, s in enumerate(siblings) if str(s.id) == after_task_id), None)
        insert_idx = idx + 1 if idx is not None else None
    if insert_idx is None:
        raise not_found("task_not_found", "目标位置任务不存在")

    prev = siblings[insert_idx - 1] if insert_idx > 0 else None
    before = siblings[insert_idx] if insert_idx < len(siblings) else None
    if prev is None and before is None:
        return task  # 同层级仅有自己，无需调整
    if prev is None:
        task.sort_order = before.sort_order - SORT_STEP
    elif before is None:
        task.sort_order = prev.sort_order + SORT_STEP  # 真落尾：最后一项 + 步长，无下一项可冲突
    elif before.sort_order - prev.sort_order >= 2:
        task.sort_order = (prev.sort_order + before.sort_order) // 2
    else:
        # 无空闲整数：整列重排回步长 SORT_STEP
        siblings.insert(insert_idx, task)
        for i, s in enumerate(siblings):
            s.sort_order = (i + 1) * SORT_STEP
            s.updated_at = datetime.now(timezone.utc)
            await s.save()
        return task
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task


async def ack_reminders(task_id: str, owner: str, snooze_minutes: Optional[int] = None) -> Task:
    """消费提醒：将该任务所有已触发提醒置 notified=True；带 snooze_minutes 时改为推迟后再触发。"""
    task = await get_task_or_404(task_id, owner)
    now = datetime.now(timezone.utc)
    changed = False
    for reminder in task.reminders or []:
        if reminder.triggered and not reminder.notified:
            if snooze_minutes:
                reminder.at = now + timedelta(minutes=snooze_minutes)
                reminder.triggered = False
            else:
                reminder.notified = True
            changed = True
    if changed:
        task.updated_at = now
        await task.save()
    return task


async def add_attachment(task_id: str, owner: str, data) -> Task:
    """登记附件引用（文件本体已上传至存储后端）。"""
    task = await get_task_or_404(task_id, owner, write=True)
    task.attachments = task.attachments or []
    task.attachments.append(
        Attachment(
            resource_id=data.resource_id,
            name=data.name,
            content_type=data.content_type,
            size=data.size,
            uploaded_by=owner,
            url=getattr(data, "url", None),
        )
    )
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task


async def upload_attachment(
    task_id: str, owner: str, filename: str, content_type: str, file_bytes: bytes
) -> Task:
    """上传附件（task/{task_id}/ 目录）并登记引用。存储后端由 STORAGE_BACKEND 决定。"""
    from app.services.storage import get_storage

    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise bad_request("invalid_attachment_type", "仅支持 png/jpg/gif/webp/bmp 图片")
    if len(file_bytes) > MAX_ATTACHMENT_SIZE:
        raise bad_request("attachment_too_large", "附件大小不能超过 5MB")
    task = await get_task_or_404(task_id, owner, write=True)
    resp = await get_storage().upload(file_bytes, filename, f"task/{task_id}")
    task.attachments = task.attachments or []
    task.attachments.append(
        Attachment(
            resource_id=resp["path"],
            name=filename,
            content_type=content_type or "application/octet-stream",
            size=len(file_bytes),
            uploaded_by=owner,
            url=resp.get("url"),
        )
    )
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task


async def remove_attachment(task_id: str, resource_id: str, owner: str) -> None:
    """移除附件引用；存储侧资源由 GC / 管理员另行清理。"""
    task = await get_task_or_404(task_id, owner, write=True)
    task.attachments = [a for a in (task.attachments or []) if a.resource_id != resource_id]
    task.updated_at = datetime.now(timezone.utc)
    await task.save()


async def get_subtasks(parent_id: str) -> List[Task]:
    return (
        await Task.find(Task.parent_id == parent_id, Task.is_deleted == False)  # noqa: E712
        .sort("sort_order")
        .to_list()
    )


async def get_subtask_counts(task_ids: List[str]) -> Dict[str, Tuple[int, int]]:
    """批量统计子任务 (total, done)，避免 N+1。"""
    if not task_ids:
        return {}
    subs = await Task.find(
        {"parent_id": {"$in": task_ids}, "is_deleted": False}
    ).to_list()
    counts: Dict[str, List[int]] = {}
    for sub in subs:
        bucket = counts.setdefault(sub.parent_id, [0, 0])
        bucket[0] += 1
        if sub.status == "done":
            bucket[1] += 1
    return {pid: (v[0], v[1]) for pid, v in counts.items()}


async def get_case_ref(task: Task) -> Tuple[Optional[str], Optional[str]]:
    """实时查询关联导图信息（不落冗余快照）：导图标题 + 节点文本。"""
    if not task.case_map_id or not is_valid_oid(task.case_map_id):
        return None, None
    case_map = await CaseMap.get(ObjectId(task.case_map_id))
    if case_map is None or case_map.is_deleted:
        return None, None
    node_text = None
    if task.case_node_id:
        versions = await CaseVersion.find(CaseVersion.map_id == task.case_map_id).sort(-CaseVersion.version_no).limit(1).to_list()
        if versions:
            node_text = _find_node_text(versions[0].root.get("root", {}), task.case_node_id)
    return case_map.title, node_text


def _find_node_text(node: dict, uid: str) -> Optional[str]:
    """在导图节点树中按 uid 找节点文本。"""
    if not isinstance(node, dict):
        return None
    data = node.get("data") or {}
    if data.get("uid") == uid:
        return data.get("text")
    for child in node.get("children") or []:
        found = _find_node_text(child, uid)
        if found is not None:
            return found
    return None
