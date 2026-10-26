"""习惯打卡对齐主流待办应用：三方式打卡/目标类型/统计（四卡+月历+概览）/周概览。"""
import pytest

BASE = "/api/v1/task/habits"
TZ = 480


def today_str() -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(minutes=TZ)).strftime("%Y-%m-%d")


@pytest.mark.asyncio
async def test_habit_checkin_modes_and_goal_type(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 手动记录模式：amount 累计
    r = await client.post(
        BASE,
        headers=headers,
        json={"name": "e2e-背单词", "checkin_mode": "manual", "target_per_day": 5, "goal_type": "amount"},
    )
    h_manual = r.json()["id"]
    r = await client.post(f"{BASE}/{h_manual}/checkin", headers=headers, json={"amount": 3})
    assert r.json()["count"] == 3
    r = await client.post(f"{BASE}/{h_manual}/checkin", headers=headers, json={"amount": 2})
    assert r.json()["count"] == 5  # 达标
    r = await client.get(BASE, headers=headers, params={"tz_offset_minutes": TZ})
    item = next(x for x in r.json()["items"] if x["id"] == h_manual)
    assert item["today_checked"] is True and item["today_count"] == 5
    assert item["checkin_mode"] == "manual" and item["goal_type"] == "amount"

    # 完成全部模式：一次补到 target
    r = await client.post(
        BASE,
        headers=headers,
        json={"name": "e2e-早睡", "checkin_mode": "all", "target_per_day": 1, "goal_type": "check"},
    )
    h_all = r.json()["id"]
    r = await client.post(f"{BASE}/{h_all}/checkin", headers=headers, json={})
    assert r.json()["count"] == 1
    # goal_type=check：count>=1 即达标；"all" 模式重复打卡保持 target 不变（完成全部语义）
    r = await client.post(f"{BASE}/{h_all}/checkin", headers=headers, json={"amount": 2})
    assert r.json()["count"] == 1

    # 自动模式：默认 +1
    r = await client.post(BASE, headers=headers, json={"name": "e2e-喝水", "checkin_mode": "auto", "target_per_day": 3})
    h_auto = r.json()["id"]
    r = await client.post(f"{BASE}/{h_auto}/checkin", headers=headers, json={})
    assert r.json()["count"] == 1

    # 心情/笔记随打卡落库
    r = await client.post(f"{BASE}/{h_auto}/checkin", headers=headers, json={"mood": 5, "note": "开心"})
    assert r.json()["count"] == 2
    r = await client.get(f"{BASE}/{h_auto}/logs", headers=headers)
    logs = r.json()["items"]
    assert any(l["mood"] == 5 and l["note"] == "开心" for l in logs)

    # 清理
    for hid in (h_manual, h_all, h_auto):
        await client.delete(f"{BASE}/{hid}", headers=headers)


@pytest.mark.asyncio
async def test_habit_stats_month_calendar_and_week(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    today = today_str()
    month = today[:7]

    r = await client.post(
        BASE,
        headers=headers,
        json={"name": "e2e-统计习惯", "freq": "daily", "target_per_day": 1, "reminders": ["09:00", "21:30"], "auto_log": False, "motto": "坚持"},
    )
    hid = r.json()["id"]
    assert r.json()["reminders"] == ["09:00", "21:30"]
    assert r.json()["auto_log"] is False and r.json()["motto"] == "坚持"

    # 今天打卡 2 次（手动量），昨天 1 次
    await client.post(f"{BASE}/{hid}/checkin", headers=headers, json={"amount": 2})
    yesterday = f"{BASE}/{hid}/checkin"
    from datetime import datetime, timedelta, timezone

    y = (datetime.now(timezone.utc) + timedelta(minutes=TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    await client.post(yesterday, headers=headers, json={"date": y})

    # 统计：月历含今天/昨天 done，四卡数值
    r = await client.get(f"{BASE}/{hid}/stats", headers=headers, params={"month": month, "tz_offset_minutes": TZ})
    s = r.json()
    assert s["month_checked"] == 2
    assert s["total_days"] == 2
    assert s["total_count"] == 3  # 2 + 1
    assert s["days"][today]["done"] is True and s["days"][today]["count"] == 2
    assert s["days"][y]["done"] is True
    assert s["month_rate"] > 0 and s["planned_days"] >= 2
    assert s["best_streak"] >= 2 and s["streak"] >= 2

    # 月历覆盖整月
    assert len(s["days"]) >= 28

    # 周概览：今天 done=1
    r = await client.get(f"{BASE}/week", headers=headers, params={"tz_offset_minutes": TZ})
    days = r.json()["days"]
    assert len(days) == 7
    t_day = next(d for d in days if d["date"] == today)
    assert t_day["done"] >= 1 and t_day["total"] >= 1

    # 归档后不计入周概览 total
    await client.patch(f"{BASE}/{hid}", headers=headers, json={"is_archived": True})
    r = await client.get(BASE + "/week", headers=headers, params={"tz_offset_minutes": TZ})
    t_day2 = next(d for d in r.json()["days"] if d["date"] == today)
    assert t_day2["total"] == t_day["total"] - 1

    # 清理
    await client.delete(f"{BASE}/{hid}", headers=headers)
