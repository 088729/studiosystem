import pytest

BASE = "/api/v1/task/focus"
HABITS = "/api/v1/task/habits"
PRESETS = "/api/v1/task/focus-presets"


@pytest.mark.asyncio
async def test_preset_habit_link_and_auto_checkin(client, admin_token):
    """常用专注关联习惯：预设携带 habit_id → 开始会话自动继承 → 完成自动打卡"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(HABITS, headers=headers, json={"name": "e2e-专注习惯", "freq": "daily"})
    habit_id = r.json()["id"]

    # 创建带 habit_id 的预设
    r = await client.post(PRESETS, headers=headers, json={"name": "e2e-专注预设", "habit_id": habit_id})
    assert r.status_code == 200
    assert r.json()["habit_id"] == habit_id

    # 更新习惯关联
    r = await client.patch(f"{PRESETS}/{r.json()['id']}", headers=headers, json={"habit_id": None})
    assert r.json()["habit_id"] is None
    r = await client.patch(f"{PRESETS}/{r.json()['id']}", headers=headers, json={"habit_id": habit_id})
    assert r.json()["habit_id"] == habit_id

    # 从预设开始：会话继承 habit_id
    r = await client.post(BASE, headers=headers, json={"preset_id": r.json()["id"], "planned_minutes": 25})
    session = r.json()
    assert session["habit_id"] == habit_id

    # 完成前习惯未打卡
    r = await client.get(HABITS, headers=headers)
    h = [x for x in r.json()["items"] if x["id"] == habit_id][0]
    assert h["today_checked"] is False

    # 完成 → 自动打卡
    r = await client.post(f"{BASE}/{session['id']}/finish", headers=headers)
    assert r.json()["status"] == "completed"
    r = await client.get(HABITS, headers=headers)
    h = [x for x in r.json()["items"] if x["id"] == habit_id][0]
    assert h["today_checked"] is True

    # 放弃不打卡：直接显式 habit_id 开始再放弃
    r = await client.post(BASE, headers=headers, json={"planned_minutes": 5, "habit_id": habit_id})
    session2 = r.json()
    assert session2["habit_id"] == habit_id
    r = await client.get(HABITS, headers=headers)
    before = [x for x in r.json()["items"] if x["id"] == habit_id][0]["today_count"]
    r = await client.post(f"{BASE}/{session2['id']}/abandon", headers=headers)
    assert r.json()["status"] == "abandoned"
    r = await client.get(HABITS, headers=headers)
    after = [x for x in r.json()["items"] if x["id"] == habit_id][0]["today_count"]
    assert after == before  # 放弃不打卡

    # 清理
    r = await client.get(PRESETS, headers=headers)
    for p in r.json()["items"]:
        if p["name"].startswith("e2e-"):
            await client.delete(f"{PRESETS}/{p['id']}", headers=headers)
    await client.delete(f"{HABITS}/{habit_id}", headers=headers)
