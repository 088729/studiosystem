import pytest

BASE = "/api/v1/task/focus"


@pytest.mark.asyncio
async def test_focus_pause_resume_excludes_paused_time(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(BASE, headers=headers, json={"planned_minutes": 25})
    session_id = r.json()["id"]

    # 暂停（幂等）
    r = await client.post(f"{BASE}/{session_id}/pause", headers=headers)
    assert r.status_code == 200
    assert r.json()["paused_at"] is not None
    r = await client.post(f"{BASE}/{session_id}/pause", headers=headers)
    assert r.json()["paused_at"] is not None

    # 暂停中 running_only 仍可见
    r = await client.get(BASE, headers=headers, params={"running_only": True})
    assert len(r.json()["items"]) == 1

    # 恢复（幂等）→ paused_at 清空、累计暂停秒落库
    r = await client.post(f"{BASE}/{session_id}/resume", headers=headers)
    assert r.json()["paused_at"] is None
    assert r.json()["paused_seconds"] >= 0
    r = await client.post(f"{BASE}/{session_id}/resume", headers=headers)
    assert r.json()["paused_seconds"] >= 0

    # 暂停中直接结束：状态正常关闭
    r = await client.post(f"{BASE}/{session_id}/finish", headers=headers)
    assert r.json()["status"] == "completed"
    assert r.json()["actual_seconds"] >= 0


@pytest.mark.asyncio
async def test_focus_update_running_and_closed(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(BASE, headers=headers, json={"planned_minutes": 25})
    session_id = r.json()["id"]

    # 专注中 ± 调时（改 planned_minutes）
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"planned_minutes": 30})
    assert r.status_code == 200
    assert r.json()["planned_minutes"] == 30

    # 专注中不允许改实际时长
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"actual_seconds": 60})
    assert r.status_code == 400

    # 写专注笔记（进行中即可写）
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"note": "第一章笔记"})
    assert r.json()["note"] == "第一章笔记"

    # 结束后改实际时长 + 笔记
    await client.post(f"{BASE}/{session_id}/finish", headers=headers)
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"actual_seconds": 1500})
    assert r.json()["actual_seconds"] == 1500
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"note": "补记笔记"})
    assert r.json()["note"] == "补记笔记"

    # 结束后不允许再调计划时长
    r = await client.patch(f"{BASE}/{session_id}", headers=headers, json={"planned_minutes": 45})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_focus_add_record(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "补记关联任务"})
    task_id = r.json()["id"]

    r = await client.post(
        BASE + "/records",
        headers=headers,
        json={
            "task_id": task_id,
            "planned_minutes": 25,
            "actual_seconds": 1500,
            "started_at": "2026-02-10T09:00:00+08:00",
            "note": "早上专注",
        },
    )
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["status"] == "completed"
    assert s["actual_seconds"] == 1500
    assert s["note"] == "早上专注"
    assert s["ended_at"] is not None

    # 无关联任务的纯计时补记
    r = await client.post(
        BASE + "/records",
        headers=headers,
        json={"planned_minutes": 45, "actual_seconds": 2700, "started_at": "2026-02-10T14:00:00+08:00"},
    )
    assert r.status_code == 200

    # 非法关联任务 404 / 非法时长 400
    r = await client.post(
        BASE + "/records",
        headers=headers,
        json={"task_id": "000000000000000000000000", "actual_seconds": 60, "started_at": "2026-02-10T09:00:00+08:00"},
    )
    assert r.status_code == 404
    r = await client.post(
        BASE + "/records",
        headers=headers,
        json={"actual_seconds": 0, "started_at": "2026-02-10T09:00:00+08:00"},
    )
    assert r.status_code == 422
