"""习惯打卡服务（模块级函数，对齐 task_service 风格）。"""
from datetime import date as _date
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.task.habit import Habit, HabitLog
from app.services.case.folder_service import is_valid_oid


def local_date_str(tz_offset_minutes: int = 0, days_ago: int = 0) -> str:
    """按客户端时区偏移（本地 - UTC 分钟数）计算本地日期字符串。"""
    local = datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes) - timedelta(days=days_ago)
    return local.strftime("%Y-%m-%d")


async def get_habit_or_404(habit_id: str, owner: str) -> Habit:
    if not is_valid_oid(habit_id):
        raise not_found("habit_not_found", "习惯不存在")
    habit = await Habit.get(ObjectId(habit_id))
    if habit is None or habit.owner != owner:
        raise not_found("habit_not_found", "习惯不存在")
    return habit


def _goal_met(habit: Habit, count: int) -> bool:
    """达标口径：goal_type=check → 当天打卡即达标；amount → count >= target_per_day。"""
    if getattr(habit, "goal_type", "amount") == "check":
        return count >= 1
    return count >= habit.target_per_day


async def list_habits(owner: str, tz_offset_minutes: int = 0, date: Optional[str] = None) -> List[Tuple[Habit, bool, int, List[bool], int, bool, int]]:
    """返回 (habit, checked, streak, 最近7天位图, count, skipped, total_days)。
    checked/count/skipped 按 date（缺省今天）；达标按 goal_type 口径；
    streak 容忍跳过日（skipped 不加不减、继续往前）。"""
    habits = await Habit.find(Habit.owner == owner).sort("sort_order").to_list()
    result = []
    today = date or local_date_str(tz_offset_minutes)
    for habit in habits:
        logs = await HabitLog.find(HabitLog.habit_id == str(habit.id)).to_list()
        counts: dict = {}
        skipped_dates: set = set()
        total_days = 0
        for log in logs:
            counts[log.date] = counts.get(log.date, 0) + (log.checkin_count or 0)
            if log.skipped:
                skipped_dates.add(log.date)
        for d, c in counts.items():
            if c > 0 and d not in skipped_dates:
                total_days += 1

        def goal_met(date_str: str) -> bool:
            return _goal_met(habit, counts.get(date_str, 0))

        today_count = counts.get(today, 0)
        today_checked = goal_met(today)
        today_skipped = today in skipped_dates and not today_checked

        # streak：连续达标天数。今天达标/跳过从今天起数，否则从昨天起数；
        # 某天达标 → +1；未达标但 skipped → 跳过该日继续（不加不减）；否则中断
        streak = 0
        offset = 0 if (today_checked or today in skipped_dates) else 1
        while True:
            day = local_date_str(tz_offset_minutes, days_ago=offset)
            if goal_met(day):
                streak += 1
            elif day in skipped_dates:
                pass  # 跳过日：不加不减
            else:
                break
            offset += 1

        week_bitmap = [goal_met(local_date_str(tz_offset_minutes, days_ago=6 - i)) for i in range(7)]
        result.append((habit, today_checked, streak, week_bitmap, today_count, today_skipped, total_days))
    return result


async def create_habit(
    name: str,
    color: Optional[str],
    owner: str,
    freq: str = "daily",
    target_per_day: int = 1,
    target_per_week: int = 7,
    start_date: Optional[str] = None,
    group: Optional[str] = None,
    icon: Optional[str] = None,
    goal_type: str = "amount",
    checkin_mode: str = "auto",
    reminders: Optional[List[str]] = None,
    auto_log: bool = True,
    motto: str = "",
) -> Habit:
    last = await Habit.find(Habit.owner == owner).sort("-sort_order").limit(1).to_list()
    habit = Habit(
        name=name,
        owner=owner,
        color=color or "#4f6ef7",
        icon=icon or "smile",
        freq=freq,
        target_per_day=target_per_day,
        target_per_week=target_per_week,
        start_date=start_date,
        group=group,
        goal_type=goal_type,
        checkin_mode=checkin_mode,
        reminders=reminders or [],
        auto_log=auto_log,
        motto=motto,
        sort_order=(last[0].sort_order + 1) if last else 0,
    )
    await habit.insert()
    return habit


async def update_habit(habit_id: str, data: dict, owner: str) -> Habit:
    habit = await get_habit_or_404(habit_id, owner)
    for key, value in data.items():
        setattr(habit, key, value)
    await habit.save()
    return habit


async def delete_habit(habit_id: str, owner: str) -> None:
    habit = await get_habit_or_404(habit_id, owner)
    await HabitLog.find(HabitLog.habit_id == habit_id).delete_many()
    await habit.delete()


async def checkin(
    habit_id: str,
    owner: str,
    date: Optional[str],
    note: Optional[str],
    tz_offset_minutes: int = 0,
    mood: Optional[int] = None,
    amount: Optional[int] = None,
    meta_only: bool = False,
) -> HabitLog:
    """同日重复打卡累计 count（对齐主流待办应用三种打卡方式）：
    - auto：+1（amount 缺省 1）
    - manual：+amount（本次手动输入的量）
    - all：直接补到 target（完成全部）
    meta_only=True 时只写心情/日志（打卡后自动弹层），不增加 count。
    若当日为跳过记录，打卡后清除 skipped 标记。mood/note 传入才覆盖。"""
    habit = await get_habit_or_404(habit_id, owner)
    date = date or local_date_str(tz_offset_minutes)
    log = await HabitLog.find_one(HabitLog.habit_id == habit_id, HabitLog.date == date)
    if meta_only:
        # 只写心情/日志（打卡后自动弹层回写）：必须已有当日记录，不增加 count
        if log is None or (log.checkin_count or 0) <= 0:
            raise bad_request("no_checkin", "当日尚无打卡记录")
        if note is not None:
            log.note = note
        if mood is not None:
            log.mood = mood
        await log.save()
        return log
    mode = getattr(habit, "checkin_mode", "auto") or "auto"
    if log:
        if mode == "all":
            log.checkin_count = max(log.checkin_count or 0, habit.target_per_day)
        else:
            log.checkin_count = (log.checkin_count or 0) + (amount or 1)
        log.skipped = False  # 打卡清除跳过标记
        if note:
            log.note = note
        if mood is not None:
            log.mood = mood
        await log.save()
        return log
    init = habit.target_per_day if mode == "all" else (amount or 1)
    log = HabitLog(habit_id=habit_id, owner=owner, date=date, checkin_count=init, note=note, mood=mood)
    await log.insert()
    return log


async def skip(habit_id: str, owner: str, date: Optional[str], tz_offset_minutes: int = 0) -> HabitLog:
    """跳过当日：不算打卡也不打断 streak。幂等（重复 skip 不报错）；当日已达标则拒绝。"""
    habit = await get_habit_or_404(habit_id, owner)
    date = date or local_date_str(tz_offset_minutes)
    log = await HabitLog.find_one(HabitLog.habit_id == habit_id, HabitLog.date == date)
    if log and (log.checkin_count or 0) >= habit.target_per_day:
        raise bad_request("already_checked", "今日已打卡，无需跳过")
    if log:
        if not log.skipped:
            log.skipped = True
            await log.save()
        return log
    log = HabitLog(habit_id=habit_id, owner=owner, date=date, checkin_count=0, skipped=True)
    await log.insert()
    return log


async def uncheckin(habit_id: str, owner: str, date: Optional[str], tz_offset_minutes: int = 0) -> None:
    """取消一次打卡：count - 1，减到 0 时删除当日记录。"""
    await get_habit_or_404(habit_id, owner)
    date = date or local_date_str(tz_offset_minutes)
    log = await HabitLog.find_one(HabitLog.habit_id == habit_id, HabitLog.date == date)
    if log is None:
        return
    if (log.checkin_count or 1) > 1:
        log.checkin_count -= 1
        await log.save()
    else:
        await log.delete()


async def list_logs(habit_id: str, owner: str, start: Optional[str], end: Optional[str]) -> List[HabitLog]:
    await get_habit_or_404(habit_id, owner)
    conditions = [HabitLog.habit_id == habit_id]
    if start:
        conditions.append(HabitLog.date >= start)
    if end:
        conditions.append(HabitLog.date <= end)
    return await HabitLog.find(*conditions).sort("-date").limit(500).to_list()


def _best_streak(habit: Habit, counts: dict, skipped_dates: set) -> int:
    """历史最高连续达标天数（跳过日不加不减）。"""
    best = cur = 0
    for d in sorted(counts.keys()):
        if _goal_met(habit, counts[d]) and d not in skipped_dates:
            cur += 1
            best = max(best, cur)
        elif d in skipped_dates:
            pass
        else:
            cur = 0
    return best


async def habit_stats(habit_id: str, owner: str, month: Optional[str], tz_offset_minutes: int = 0) -> dict:
    """详情四卡 + 月历打卡表 + 月度概览（对齐主流待办应用习惯统计）。"""
    habit = await get_habit_or_404(habit_id, owner)
    today = local_date_str(tz_offset_minutes)
    month = month or today[:7]
    month_start = f"{month}-01"
    # 次月首日
    y, m = int(month[:4]), int(month[5:7])
    next_m = f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"

    logs = await HabitLog.find(
        HabitLog.habit_id == habit_id,
        HabitLog.date >= month_start,
        HabitLog.date < next_m,
    ).to_list()
    all_logs = await HabitLog.find(HabitLog.habit_id == habit_id).to_list()
    counts: dict = {}
    skipped_dates: set = set()
    total_days = 0
    total_count_days = 0  # 累计打卡次数
    for log in all_logs:
        c = log.checkin_count or 0
        counts[log.date] = counts.get(log.date, 0) + c
        if log.skipped:
            skipped_dates.add(log.date)
    for d, c in counts.items():
        if c > 0 and d not in skipped_dates:
            total_days += 1
            total_count_days += c

    # 月历：每天 {count, done, skipped}
    days = {}
    month_checked = 0
    planned = 0

    cursor = _date.fromisoformat(month_start)
    end_day = min(_date.fromisoformat(next_m) - timedelta(days=1), _date.fromisoformat(today))
    start_day = _date.fromisoformat(month_start)
    if habit.start_date:
        start_day = max(start_day, _date.fromisoformat(habit.start_date))
    while cursor <= _date.fromisoformat(next_m) - timedelta(days=1):
        key = cursor.isoformat()
        c = counts.get(key, 0)
        done = _goal_met(habit, c) and key not in skipped_dates
        days[key] = {"count": c, "done": done, "skipped": key in skipped_dates}
        if cursor <= end_day and cursor >= start_day:
            planned += 1
            if done:
                month_checked += 1
        cursor += timedelta(days=1)

    # streak：同 list_habits 口径
    streak = 0
    offset = 0 if (today in counts and _goal_met(habit, counts[today])) or today in skipped_dates else 1
    while True:
        day = local_date_str(tz_offset_minutes, days_ago=offset)
        if _goal_met(habit, counts.get(day, 0)) and day not in skipped_dates:
            streak += 1
        elif day in skipped_dates:
            pass
        else:
            break
        offset += 1

    return {
        "month": month,
        "month_checked": month_checked,
        "total_days": total_days,
        "total_count": total_count_days,
        "month_rate": round(month_checked * 100 / planned, 1) if planned else 0,
        "planned_days": planned,
        "best_streak": _best_streak(habit, counts, skipped_dates),
        "streak": streak,
        "days": days,
    }


async def week_overview(owner: str, tz_offset_minutes: int = 0) -> List[dict]:
    """本周概览：周一~周日每天达标习惯数/习惯总数（左上圆环条）。"""
    habits = await Habit.find(Habit.owner == owner, Habit.is_archived == False).sort("sort_order").to_list()  # noqa: E712
    today = local_date_str(tz_offset_minutes)
    weekday = (_date_weekday(today))
    monday = (_date.fromisoformat(today) - timedelta(days=weekday)).isoformat()
    ids = [str(h.id) for h in habits]
    logs = await HabitLog.find({"habit_id": {"$in": ids}}, HabitLog.date >= monday).to_list() if ids else []
    by_habit: dict = {}
    skipped: dict = {}
    for log in logs:
        by_habit.setdefault(log.habit_id, {})[log.date] = (log.checkin_count or 0)
        if log.skipped:
            skipped.setdefault(log.habit_id, set()).add(log.date)
    days = []
    for i in range(7):
        d = (_date.fromisoformat(monday) + timedelta(days=i)).isoformat()
        done = 0
        for h in habits:
            c = by_habit.get(str(h.id), {}).get(d, 0)
            is_skip = d in skipped.get(str(h.id), set())
            if _goal_met(h, c) and not is_skip:
                done += 1
        days.append({"date": d, "done": done, "total": len(habits)})
    return days


def _date_weekday(date_str: str) -> int:
    return _date.fromisoformat(date_str).weekday()
