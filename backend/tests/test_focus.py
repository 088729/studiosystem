import pytest

BASE = "/api/v1/task/focus"


@pytest.mark.asyncio
async def test_focus_lifecycle(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 开始（纯计时）
    r = await client.post(BASE, headers=headers, json={"planned_minutes": 25})
    assert r.status_code == 200, r.text
    session = r.json()
    assert session["status"] == "running"
    assert session["planned_minutes"] == 25

    # 并发 running 拒绝
    r = await client.post(BASE, headers=headers, json={"planned_minutes": 25})
    assert r.status_code == 400

    # running_only 查询
    r = await client.get(BASE, headers=headers, params={"running_only": True})
    assert len(r.json()["items"]) == 1

    # 完成（幂等）
    r = await client.post(f"{BASE}/{session['id']}/finish", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    r = await client.post(f"{BASE}/{session['id']}/finish", headers=headers)
    assert r.json()["status"] == "completed"

    # 统计
    r = await client.get(f"{BASE}/stats", headers=headers, params={"tz_offset_minutes": 480})
    assert r.json()["today_completed"] >= 1
    assert r.json()["total_completed"] >= 1


@pytest.mark.asyncio
async def test_focus_with_task_and_abandon(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "专注任务"})
    task_id = r.json()["id"]

    r = await client.post(BASE, headers=headers, json={"task_id": task_id, "planned_minutes": 15})
    assert r.status_code == 200
    session_id = r.json()["id"]
    assert r.json()["task_id"] == task_id

    # 放弃（幂等）
    r = await client.post(f"{BASE}/{session_id}/abandon", headers=headers)
    assert r.json()["status"] == "abandoned"
    r = await client.post(f"{BASE}/{session_id}/finish", headers=headers)
    assert r.json()["status"] == "abandoned"  # 非 running 不变更

    # 关联不存在任务 → 404
    r = await client.post(BASE, headers=headers, json={"task_id": "000000000000000000000000"})
    assert r.status_code == 404

    # 非法时长 → 400（负数）
    r = await client.post(BASE, headers=headers, json={"planned_minutes": -1})
    assert r.status_code == 400
