import pytest

BASE = "/api/v1/task/habits"


@pytest.mark.asyncio
async def test_habit_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(BASE, headers=headers, json={"name": "晨会复盘", "color": "#ff0000"})
    assert r.status_code == 200, r.text
    habit = r.json()
    assert habit["color"] == "#ff0000"
    assert habit["today_checked"] is False
    assert habit["streak"] == 0

    r = await client.get(BASE, headers=headers)
    assert any(item["id"] == habit["id"] for item in r.json()["items"])

    r = await client.patch(f"{BASE}/{habit['id']}", headers=headers, json={"name": "复盘"})
    assert r.json()["name"] == "复盘"

    r = await client.delete(f"{BASE}/{habit['id']}", headers=headers)
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{habit['id']}/logs", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_checkin_idempotent_and_uncheckin(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(BASE, headers=headers, json={"name": "每日站会"})
    habit_id = r.json()["id"]

    # 打卡（显式日期）
    r = await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": "2026-08-16"})
    assert r.status_code == 200
    assert r.json()["date"] == "2026-08-16"

    # 幂等：重复打卡不报错
    r = await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": "2026-08-16"})
    assert r.status_code == 200

    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    assert len([i for i in r.json()["items"] if i["date"] == "2026-08-16"]) == 1

    # 取消打卡（count 语义：同日两次打卡 count=2，需取消两次才删除当日记录）
    r = await client.delete(f"{BASE}/{habit_id}/checkin", headers=headers, params={"date": "2026-08-16"})
    assert r.status_code == 200
    r = await client.delete(f"{BASE}/{habit_id}/checkin", headers=headers, params={"date": "2026-08-16"})
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    assert all(i["date"] != "2026-08-16" for i in r.json()["items"])


@pytest.mark.asyncio
async def test_streak_and_today_checked(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    tz = 480  # 东八区

    r = await client.post(BASE, headers=headers, json={"name": "写日报"})
    habit_id = r.json()["id"]

    # 今天 + 昨天 + 前天打卡 → streak=3
    from app.services.task.habit_service import local_date_str

    for days_ago in (0, 1, 2):
        date = local_date_str(tz, days_ago)
        await client.post(f"{BASE}/{habit_id}/checkin?tz_offset_minutes={tz}", headers=headers, json={"date": date})

    r = await client.get(BASE, headers=headers, params={"tz_offset_minutes": tz})
    item = next(i for i in r.json()["items"] if i["id"] == habit_id)
    assert item["today_checked"] is True
    assert item["streak"] == 3
    assert item["week_bitmap"][-1] is True  # 最后一位是今天

    # 删除习惯级联删 logs
    r = await client.delete(f"{BASE}/{habit_id}", headers=headers)
    assert r.status_code == 200
    r = await client.get(BASE, headers=headers)
    assert all(i["id"] != habit_id for i in r.json()["items"])


# ---------- 跳过打卡（skipped） ----------

@pytest.mark.asyncio
async def test_skip_flow(client, admin_token):
    """skip 幂等、列表 today_skipped/today_checked、logs 带 skipped、取消跳过、checkin 清除 skipped。"""
    from app.services.task.habit_service import local_date_str

    headers = {"Authorization": f"Bearer {admin_token}"}
    tz = 0

    r = await client.post(BASE, headers=headers, json={"name": "跳绳"})
    habit_id = r.json()["id"]
    today = local_date_str(tz)

    # 跳过今天（body 可空）
    r = await client.post(f"{BASE}/{habit_id}/skip?tz_offset_minutes={tz}", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["skipped"] is True
    assert r.json()["date"] == today

    # 幂等：重复 skip 不报错
    r = await client.post(f"{BASE}/{habit_id}/skip?tz_offset_minutes={tz}", headers=headers, json={"date": today})
    assert r.status_code == 200

    # 列表：today_skipped=True、today_checked 仍 False
    r = await client.get(BASE, headers=headers, params={"tz_offset_minutes": tz})
    item = next(i for i in r.json()["items"] if i["id"] == habit_id)
    assert item["today_skipped"] is True
    assert item["today_checked"] is False

    # logs 返回 skipped 字段
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    log = next(i for i in r.json()["items"] if i["date"] == today)
    assert log["skipped"] is True
    assert log["count"] == 0

    # 取消跳过：纯跳过记录被 uncheckin 直接删除
    r = await client.delete(f"{BASE}/{habit_id}/checkin", headers=headers, params={"date": today})
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    assert all(i["date"] != today for i in r.json()["items"])

    # 重新 skip 后 checkin：清除 skipped 标记
    await client.post(f"{BASE}/{habit_id}/skip?tz_offset_minutes={tz}", headers=headers)
    r = await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today})
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    log = next(i for i in r.json()["items"] if i["date"] == today)
    assert log["skipped"] is False
    assert log["count"] == 1


@pytest.mark.asyncio
async def test_skip_rejected_when_already_checked(client, admin_token):
    """当日已达标（count >= target_per_day）时 skip 返回 400。"""
    from app.services.task.habit_service import local_date_str

    headers = {"Authorization": f"Bearer {admin_token}"}
    tz = 0

    r = await client.post(BASE, headers=headers, json={"name": "喝八杯水"})
    habit_id = r.json()["id"]
    today = local_date_str(tz)

    await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today})
    r = await client.post(f"{BASE}/{habit_id}/skip", headers=headers, json={"date": today})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_streak_tolerates_skipped_days(client, admin_token):
    """streak 跨越跳过日：3 天前达标、2 天前 skipped、昨天达标，今天未打卡未跳过
    → 从昨天起数：昨天达标 streak=1，前天 skip 跳过（不加不减），3 天前达标 streak=2。"""
    from app.services.task.habit_service import local_date_str

    headers = {"Authorization": f"Bearer {admin_token}"}
    tz = 0

    r = await client.post(BASE, headers=headers, json={"name": "背单词"})
    habit_id = r.json()["id"]

    await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": local_date_str(tz, 3)})
    await client.post(f"{BASE}/{habit_id}/skip", headers=headers, json={"date": local_date_str(tz, 2)})
    await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": local_date_str(tz, 1)})

    r = await client.get(BASE, headers=headers, params={"tz_offset_minutes": tz})
    item = next(i for i in r.json()["items"] if i["id"] == habit_id)
    assert item["today_checked"] is False
    assert item["today_skipped"] is False
    assert item["streak"] == 2  # 若 skip 会断签则只有 1

    # 今天也 skip 后：streak 从今天起数，今天 skip 跳过，语义不变仍为 2，且 today_skipped=True
    await client.post(f"{BASE}/{habit_id}/skip?tz_offset_minutes={tz}", headers=headers)
    r = await client.get(BASE, headers=headers, params={"tz_offset_minutes": tz})
    item = next(i for i in r.json()["items"] if i["id"] == habit_id)
    assert item["today_skipped"] is True
    assert item["streak"] == 2


@pytest.mark.asyncio
async def test_checkin_mood(client, admin_token):
    """checkin 带 mood → logs 返回 mood；再次 checkin 传新 mood 覆盖、不传则保留。"""
    from app.services.task.habit_service import local_date_str

    headers = {"Authorization": f"Bearer {admin_token}"}
    today = local_date_str(0)

    r = await client.post(BASE, headers=headers, json={"name": "冥想"})
    habit_id = r.json()["id"]

    # 打卡带心情
    r = await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today, "mood": 4})
    assert r.status_code == 200, r.text
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    log = next(i for i in r.json()["items"] if i["date"] == today)
    assert log["mood"] == 4

    # 再次打卡传新 mood → 覆盖
    await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today, "mood": 5})
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    log = next(i for i in r.json()["items"] if i["date"] == today)
    assert log["mood"] == 5

    # 不传 mood → 保留
    await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today})
    r = await client.get(f"{BASE}/{habit_id}/logs", headers=headers)
    log = next(i for i in r.json()["items"] if i["date"] == today)
    assert log["mood"] == 5

    # 非法 mood → 422
    r = await client.post(f"{BASE}/{habit_id}/checkin", headers=headers, json={"date": today, "mood": 6})
    assert r.status_code == 422
