import calendar
from datetime import datetime, timedelta
from typing import Optional

from app.models.task.task import RecurrenceRule


def _clamp_day(year: int, month: int, day: int) -> int:
    """月末 clamp 到当月最后一天（如 1/31 → 2/28）。"""
    return min(day, calendar.monthrange(year, month)[1])


def _add_months(base: datetime, months: int) -> datetime:
    total = base.year * 12 + base.month - 1 + months
    year, month = divmod(total, 12)
    month += 1
    return base.replace(year=year, month=month, day=_clamp_day(year, month, base.day))


def next_due(rule: RecurrenceRule, base: datetime) -> Optional[datetime]:
    """按规则计算下一次 due_at（保留 base 的时分秒）。无法计算时返回 None。"""
    interval = max(rule.interval, 1)

    if rule.freq == "daily":
        return base + timedelta(days=interval)

    if rule.freq == "weekly":
        if not rule.by_weekday:  # 空 = 按当前 due_at 的星期几
            return base + timedelta(weeks=interval)
        start = base + timedelta(weeks=interval - 1) if interval > 1 else base
        for i in range(1, 7 * interval + 1):
            candidate = start + timedelta(days=i)
            if candidate.weekday() in rule.by_weekday:
                return candidate
        return None

    if rule.freq == "monthly":
        days = sorted(rule.by_monthday) or [base.day]  # 空 = 按当前 due_at 的日号
        # B6：仅 interval=1 时允许本月内取更晚的命中日；interval>1 必须跨 interval 月
        later = [d for d in days if d > base.day] if rule.by_monthday and interval == 1 else []
        if later:
            return base.replace(day=_clamp_day(base.year, base.month, later[0]))
        nxt = _add_months(base, interval)
        return nxt.replace(day=_clamp_day(nxt.year, nxt.month, days[0]))

    if rule.freq == "yearly":
        try:
            return base.replace(year=base.year + interval)
        except ValueError:  # 2/29 → 2/28
            return base.replace(year=base.year + interval, day=28)

    return None


def should_stop(rule: RecurrenceRule, next_at: Optional[datetime]) -> bool:
    """结束条件：by_date 超过 end_date、after_count 达到 count（调用前 occurrences_completed 已 +1）。"""
    if next_at is None:
        return True
    if rule.end_type == "by_date" and rule.end_date:
        end_date = rule.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=next_at.tzinfo)
        if next_at > end_date:
            return True
    if rule.end_type == "after_count" and rule.count:
        if rule.occurrences_completed >= rule.count:
            return True
    return False
