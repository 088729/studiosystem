"""Task adapter: compact formatting, quick-add natural-language parsing.

Quick-add syntax (mirrors the frontend parser in TaskQuickAdd.vue):
    #清单 !优先级 @日期 ~标签
e.g. 「@明天 !高 ~回归 #登录」
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

PRIORITY_MAP = {"无": 0, "低": 1, "中": 2, "高": 3}
PRIORITY_REVERSE = {v: k for k, v in PRIORITY_MAP.items()}
STATUS_LABELS = {
    "todo": "待办",
    "done": "已完成",
    "skipped": "已跳过",
    "archived": "已归档",
}

_quick_add_re = re.compile(
    r"(?P<tag>#[^\s#@!~]+)|(?P<priority>![^\s#@!~]+)|(?P<date>@[^\s#@!~]+)|(?P<label>~[^\s#@!~]+)"
)


def parse_quick_add(text: str, *, today: date | None = None) -> dict[str, Any]:
    """Split natural language into (title, list_name, priority, due_at, tags).

    Pure function — list name resolution to list_id happens in the tool layer.
    """
    today = today or date.today()
    fields: dict[str, Any] = {"tags": []}
    title_parts: list[str] = []

    def due_from_token(tok: str) -> str:
        body = tok[1:]
        if body == "今天":
            d = today
        elif body == "明天":
            d = today + timedelta(days=1)
        elif body == "后天":
            d = today + timedelta(days=2)
        elif body == "下周":
            d = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        elif body == "周末":
            d = today + timedelta(days=(5 - today.weekday()) % 7)
        else:
            m = re.fullmatch(r"(\d{1,2})月(\d{1,2})[日号]?", body)
            if m:
                d = date(today.year, int(m.group(1)), int(m.group(2)))
            else:
                m = re.fullmatch(r"(\d{1,2})[日号]", body)
                if m:
                    d = date(today.year, today.month, int(m.group(1)))
                else:
                    try:
                        d = date.fromisoformat(body)
                    except ValueError:
                        raise ValueError(f"无法识别日期: @{body}") from None
        return d.isoformat()

    pos = 0
    for m in _quick_add_re.finditer(text):
        gap = text[pos : m.start()]
        if gap.strip():
            title_parts.append(gap.strip())
        pos = m.end()
        if m.group("tag"):
            fields["list_name"] = m.group("tag")[1:]
        elif m.group("priority"):
            raw = m.group("priority")[1:]
            fields["priority"] = PRIORITY_MAP.get(raw)
            if fields["priority"] is None:
                if raw.isdigit() and 0 <= int(raw) <= 3:
                    fields["priority"] = int(raw)
                else:
                    raise ValueError(f"无法识别优先级: !{raw}（可用：无/低/中/高 或 0-3）")
        elif m.group("date"):
            fields["due_at"] = due_from_token(m.group("date"))
        elif m.group("label"):
            fields["tags"].append(m.group("label")[1:])
    tail = text[pos:].strip()
    if tail:
        title_parts.append(tail)

    title = " ".join(title_parts).strip()
    if not title:
        raise ValueError("任务标题为空（quick-add 文本解析后没有剩余内容）")
    fields["title"] = title
    return fields


def format_task_line(task: dict[str, Any]) -> str:
    """One-line compact task rendering."""
    parts = [f"- [{task.get('id')}] {task.get('title', '')}"]
    status = task.get("status")
    if status and status != "todo":
        parts.append(f"({STATUS_LABELS.get(status, status)})")
    due = task.get("due_at")
    if due:
        parts.append(f"截止 {str(due)[:10]}")
    prio = PRIORITY_REVERSE.get(task.get("priority"), None)
    if prio:
        parts.append(f"!{prio}")
    if task.get("list_id"):
        parts.append(f"#{task['list_id']}")
    if task.get("tags"):
        parts.append("~" + "~".join(task["tags"]))
    if task.get("subtask_total"):
        parts.append(f"子任务 {task.get('subtask_done', 0)}/{task['subtask_total']}")
    return " ".join(parts)
