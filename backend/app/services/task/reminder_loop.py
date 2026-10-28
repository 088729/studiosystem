import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.task.task import Task

logger = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def scan_due_reminders(now: Optional[datetime] = None, batch_size: int = 200) -> int:
    """扫描到点提醒：status=todo 且未删除 且 reminders.at <= now 且 triggered=False。
    命中后标记 triggered=True（notified 保持 False，等前端 ack）。返回触发条数。"""
    now = now or datetime.now(timezone.utc)
    tasks = await Task.find(
        {
            "status": "todo",
            "is_deleted": False,
            "reminders": {"$elemMatch": {"at": {"$lte": now}, "triggered": {"$ne": True}}},
        }
    ).limit(batch_size).to_list()

    hit = 0
    for task in tasks:
        changed = False
        for reminder in task.reminders:
            if not reminder.triggered and _ensure_aware(reminder.at) <= now:
                reminder.triggered = True
                changed = True
                hit += 1
                logger.info("提醒触发: task_id=%s title=%s at=%s", task.id, task.title, reminder.at)
        if changed:
            task.updated_at = now
            await task.save()
    return hit


_reminder_task: Optional[asyncio.Task] = None


async def _reminder_loop(interval_seconds: int = 45):
    """每 45s 扫一次到点提醒。"""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await scan_due_reminders()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("提醒调度循环异常，60s 后重试")
            await asyncio.sleep(60)


def start_reminder_loop(interval_seconds: int = 45):
    global _reminder_task
    if _reminder_task is None or _reminder_task.done():
        _reminder_task = asyncio.create_task(_reminder_loop(interval_seconds))


def stop_reminder_loop():
    global _reminder_task
    if _reminder_task and not _reminder_task.done():
        _reminder_task.cancel()
