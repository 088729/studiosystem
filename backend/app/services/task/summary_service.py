"""任务摘要生成（对齐主流待办应用「摘要」智能清单）：按配置聚合任务，输出分组结构 + markdown 文本。

口径：done 任务按 completed_at ∈ [start, end)；todo 任务按 due_at ∈ [start, end)；
均强制 owner=当前用户、排除已删除与笔记（is_note）。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from beanie.operators import In, Or
from bson import ObjectId

from app.models.task.task import Task
from app.models.task.task_list import TaskList
from app.services.task.task_service import _day_bounds_utc

RANGES = ("today", "yesterday", "this_week", "last_week", "this_month", "custom")

_GROUP_DONE = "已完成"
_GROUP_TODO = "未完成"


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_range(cfg: dict):
    """返回 (start_utc, end_utc, label)。本周/上周按周一为一周开始（对齐主流待办应用中国版）。"""
    tz = int(cfg.get("tz_offset_minutes") or 0)
    today_start, tomorrow, _, _ = _day_bounds_utc(tz)
    local_today = today_start + timedelta(minutes=tz)
    r = cfg.get("range", "this_week")
    if r == "today":
        start, end = today_start, tomorrow
    elif r == "yesterday":
        start, end = today_start - timedelta(days=1), today_start
    elif r in ("this_week", "last_week"):
        monday_local = local_today - timedelta(days=local_today.weekday())
        this_week_start = monday_local - timedelta(minutes=tz)
        start, end = this_week_start, this_week_start + timedelta(days=7)
        if r == "last_week":
            start, end = this_week_start - timedelta(days=7), this_week_start
    elif r == "this_month":
        month_start_local = local_today.replace(day=1)
        if month_start_local.month == 12:
            next_month_local = month_start_local.replace(year=month_start_local.year + 1, month=1)
        else:
            next_month_local = month_start_local.replace(month=month_start_local.month + 1)
        start = month_start_local - timedelta(minutes=tz)
        end = next_month_local - timedelta(minutes=tz)
    else:  # custom：start/end 为 ISO 时间；带时区按绝对时间解释，无时区按客户端时区解释
        raw_s = datetime.fromisoformat(str(cfg["start"]).replace("Z", "+00:00"))
        raw_e = datetime.fromisoformat(str(cfg["end"]).replace("Z", "+00:00"))
        start = (
            raw_s.astimezone(timezone.utc)
            if raw_s.tzinfo is not None
            else raw_s.replace(tzinfo=timezone.utc) - timedelta(minutes=tz)
        )
        end = (
            raw_e.astimezone(timezone.utc)
            if raw_e.tzinfo is not None
            else raw_e.replace(tzinfo=timezone.utc) - timedelta(minutes=tz)
        )
    # 区间标签：本地日期「M月D日」，跨天「M月D日-M月D日」（end 为开区间，减一天）
    start_local = start + timedelta(minutes=tz)
    end_local = end + timedelta(minutes=tz) - timedelta(microseconds=1)
    if start_local.date() == end_local.date():
        label = f"{start_local.month}月{start_local.day}日"
    else:
        label = f"{start_local.month}月{start_local.day}日-{end_local.month}月{end_local.day}日"
    return start, end, label


async def generate_summary(owner: str, cfg: dict) -> dict:
    start, end, label = _resolve_range(cfg)
    statuses = cfg.get("statuses") or ["done", "todo"]

    base_conds = [Task.owner == owner, Task.is_deleted == False, Task.is_note == False]  # noqa: E712
    # 筛选：清单（"inbox" 表示收集箱）/标签（任一命中）/优先级/负责人
    list_ids = cfg.get("list_ids") or []
    if list_ids:
        or_conds = []
        ids = [i for i in list_ids if i and i != "inbox"]
        if "inbox" in list_ids:
            or_conds.append(Task.list_id == None)  # noqa: E711
        if ids:
            or_conds.append(In(Task.list_id, ids))
        if or_conds:
            base_conds.append(Or(*or_conds) if len(or_conds) > 1 else or_conds[0])
    tags = cfg.get("tags") or []
    if tags:
        base_conds.append(In(Task.tags, tags))
    priorities = cfg.get("priorities") or []
    if priorities:
        base_conds.append(In(Task.priority, priorities))
    assignees = cfg.get("assignees") or []
    if assignees:
        base_conds.append(In(Task.assignee, assignees))

    done, todo = [], []
    if "done" in statuses:
        done = await Task.find(
            *base_conds, Task.status == "done", Task.completed_at >= start, Task.completed_at < end
        ).sort("-completed_at").to_list()
    if "todo" in statuses:
        todo = await Task.find(
            *base_conds, Task.status == "todo", Task.due_at != None, Task.due_at >= start, Task.due_at < end  # noqa: E711
        ).sort("due_at").to_list()

    # 清单名映射（按 id 直接取，含共享清单）
    name_map = {}
    need = {t.list_id for t in done + todo if t.list_id}
    if need:
        lists = await TaskList.find(In(TaskList.id, [ObjectId(v) for v in need])).to_list()
        name_map = {str(l.id): l.name for l in lists}

    show = cfg.get("show") or ["date"]
    group_by = cfg.get("group_by", "status")

    def _item(t: Task, status: str) -> dict:
        date_val = t.completed_at if status == "done" else t.due_at
        return {
            "title": t.title,
            "status": status,
            "date": date_val.isoformat() if date_val else None,
            "date_label": f"{date_val.month}月{date_val.day}日" if date_val else None,
            "list_name": name_map.get(t.list_id) if t.list_id else "收集箱",
            "priority": t.priority or 0,
        }

    def _bullet(it: dict) -> str:
        parts = []
        if "date" in show and it["date_label"]:
            parts.append(f"[{it['date_label']}]")
        prio = {1: "[低]", 2: "[中]", 3: "[高]"}.get(it["priority"]) if "priority" in show else None
        line = f"- {' '.join(parts)} {it['title']}".strip()
        if prio:
            line += f" {prio}"
        if "list" in show and it["list_name"]:
            line += f"（{it['list_name']}）"
        return line

    groups = []
    if group_by == "list":
        by_list = {}
        order = []
        for t, st in [(t, "done") for t in done] + [(t, "todo") for t in todo]:
            nm = name_map.get(t.list_id) if t.list_id else "收集箱"
            if nm not in by_list:
                by_list[nm] = []
                order.append(nm)
            by_list[nm].append(_item(t, st))
        groups = [{"label": nm, "items": by_list[nm]} for nm in order]
    else:
        if done:
            groups.append({"label": _GROUP_DONE, "items": [_item(t, "done") for t in done]})
        if todo:
            groups.append({"label": _GROUP_TODO, "items": [_item(t, "todo") for t in todo]})

    md_lines = [f"# {label}", ""]
    for g in groups:
        md_lines.append(f"## {g['label']}")
        md_lines.extend(_bullet(it) for it in g["items"])
        md_lines.append("")

    return {
        "range_label": label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "groups": groups,
        "markdown": "\n".join(md_lines).strip(),
        "total": sum(len(g["items"]) for g in groups),
    }
