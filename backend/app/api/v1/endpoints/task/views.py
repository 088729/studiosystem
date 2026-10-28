import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import require_perm
from app.api.v1.endpoints.task.tasks import _task_out
from app.models.task.task import Task
from app.models.user import User
from app.services.task import task_service

router = APIRouter()


@router.get("/pending-reminders")
async def pending_reminders(current_user: User = Depends(require_perm("task:view"))):
    """待消费提醒（triggered=True 且 notified=False），前端轮询用。"""
    tasks = await Task.find(
        {
            "owner": current_user.username,
            "is_deleted": False,
            "status": "todo",  # 已完成任务不再返回待消费提醒（B3）
            "reminders": {"$elemMatch": {"triggered": True, "notified": False}},
        }
    ).to_list()

    items = [
        {
            "task_id": str(task.id),
            "title": task.title,
            "due_at": task.due_at,
            "priority": task.priority,
            "persistent": task.persistent_reminder,
            "remind_ats": [r.at for r in task.reminders if r.triggered and not r.notified],
        }
        for task in tasks
    ]
    return {"items": items}


@router.get("/stream")
async def reminder_stream(current_user: User = Depends(require_perm("task:view"))):
    """SSE 推送待消费提醒。前端用 fetch 流式读取（原生 EventSource 无法带 JWT header）。"""

    async def event_gen():
        while True:
            try:
                tasks = await Task.find(
                    {
                        "owner": current_user.username,
                        "is_deleted": False,
                        "status": "todo",
                        "reminders": {"$elemMatch": {"triggered": True, "notified": False}},
                    }
                ).to_list()
                if tasks:
                    items = [
                        {
                            "task_id": str(task.id),
                            "title": task.title,
                            "due_at": task.due_at,
                            "priority": task.priority,
                            "persistent": task.persistent_reminder,
                            "remind_ats": [r.at for r in task.reminders if r.triggered and not r.notified],
                        }
                        for task in tasks
                    ]
                    yield f"data: {json.dumps(items, default=str)}\n\n"
                yield ": heartbeat\n\n"  # 心跳防代理断连
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001
                await asyncio.sleep(15)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/calendar")
async def calendar_view(
    start: datetime,
    end: datetime,
    current_user: User = Depends(require_perm("task:view")),
):
    """日历区间查询：含 todo+done（前端划线区分），子任务不上日历。"""
    tasks = (
        await Task.find(
            Task.owner == current_user.username,
            Task.is_deleted == False,  # noqa: E712
            Task.parent_id == None,  # noqa: E711
            Task.due_at != None,  # noqa: E711
            Task.due_at >= start,
            Task.due_at < end,
        )
        .sort("due_at")
        .limit(500)
        .to_list()
    )
    return {"items": [_task_out(t) for t in tasks]}


@router.get("/tags")
async def tag_counts(current_user: User = Depends(require_perm("task:view"))):
    """按标签聚合任务数（owner 隔离），供侧栏「标签」分组。"""
    pipeline = [
        {"$match": {"owner": current_user.username, "is_deleted": False, "parent_id": None}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await Task.get_motor_collection().aggregate(pipeline).to_list(length=None)
    return {"items": [{"tag": r["_id"], "count": r["count"]} for r in rows]}


@router.get("/summary")
async def summary(
    tz_offset_minutes: int = Query(0, ge=-840, le=840),
    current_user: User = Depends(require_perm("task:view")),
):
    """统计：今日待办（含逾期）、逾期数、已完成总数，及按清单/智能清单的未完成聚合。"""
    today_start, tomorrow_start, day_after, next7 = task_service._day_bounds_utc(tz_offset_minutes)
    base = [
        Task.owner == current_user.username,
        Task.is_deleted == False,  # noqa: E712
        Task.parent_id == None,  # noqa: E711
    ]
    overdue = await Task.find(
        *base, Task.status == "todo", Task.due_at != None, Task.due_at < today_start  # noqa: E711
    ).count()
    today_todo = await Task.find(
        *base, Task.status == "todo", Task.due_at != None, Task.due_at < tomorrow_start  # noqa: E711
    ).count()
    completed_total = await Task.find(*base, Task.status == "done").count()

    # 按清单聚合未完成数（list_id=None 即收集箱）
    by_list_rows = await Task.get_motor_collection().aggregate([
        {"$match": {"owner": current_user.username, "is_deleted": False, "parent_id": None, "status": "todo"}},
        {"$group": {"_id": "$list_id", "count": {"$sum": 1}}},
    ]).to_list(length=None)
    by_list = [{"list_id": r["_id"], "todo": r["count"]} for r in by_list_rows]

    return {
        "today_todo": today_todo,
        "overdue": overdue,
        "completed_total": completed_total,
        "by_list": by_list,
        "by_smart": {
            "inbox": next((b["todo"] for b in by_list if b["list_id"] is None), 0),
            "today": today_todo,
            "tomorrow": await Task.find(
                *base, Task.status == "todo", Task.due_at >= tomorrow_start, Task.due_at < day_after
            ).count(),
            "next7": await Task.find(
                *base, Task.status == "todo", Task.due_at != None, Task.due_at < next7  # noqa: E711
            ).count(),
        },
    }
