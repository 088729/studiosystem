"""第二期：常用专注预设（CRUD/归档/统计/预设启动）。"""
import pytest
from datetime import date, datetime, timedelta, timezone

BASE = "/api/v1/task/focus-presets"
FOCUS = "/api/v1/task/focus"


@pytest.mark.asyncio
async def test_preset_crud_archive_list(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 关联任务
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "阅读任务"})
    task_id = r.json()["id"]

    # 创建（番茄计时）
    r = await client.post(
        BASE,
        headers=headers,
        json={
            "name": "每日阅读",
            "icon": "📖",
            "color": "#22c55e",
            "mode": "countdown",
            "duration_minutes": 25,
            "task_id": task_id,
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()
    pid = p["id"]
    assert p["name"] == "每日阅读" and p["mode"] == "countdown"
    assert p["task_id"] == task_id and p["archived"] is False
    assert p["sort_order"] >= 1 and p["total_seconds"] == 0

    # 校验：空名 / 非法模式 / 非法时长
    r = await client.post(BASE, headers=headers, json={"name": "  "})
    assert r.status_code == 400
    r = await client.post(BASE, headers=headers, json={"name": "x", "mode": "weird"})
    assert r.status_code == 400
    r = await client.post(BASE, headers=headers, json={"name": "x", "duration_minutes": 0})
    assert r.status_code == 422

    # 编辑：改名 + 正计时
    r = await client.patch(BASE + f"/{pid}", headers=headers, json={"name": "晨读", "mode": "stopwatch"})
    assert r.status_code == 200
    assert r.json()["name"] == "晨读" and r.json()["mode"] == "stopwatch"

    # 累计时长：补记两条（今天 + 3 天前）
    today = datetime.now(timezone.utc)
    three_days_ago = today - timedelta(days=3)
    for started, seconds in ((today, 1500), (three_days_ago, 1800)):
        r = await client.post(
            FOCUS + "/records",
            headers=headers,
            json={
                "preset_id": pid,
                "task_id": task_id,
                "planned_minutes": 25,
                "actual_seconds": seconds,
                "started_at": started.isoformat(),
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["preset_id"] == pid

    # 列表带累计秒
    r = await client.get(BASE, headers=headers)
    item = next(x for x in r.json()["items"] if x["id"] == pid)
    assert item["total_seconds"] == 3300

    # 详情统计：总时长 55m、今日 25m、专注 2 天
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    r = await client.get(BASE + f"/{pid}/stats", headers=headers, params={"week_start": monday})
    s = r.json()
    assert s["total_minutes"] == 55
    assert s["today_minutes"] == 25
    assert s["days"] == 2
    assert 25 <= sum(s["week_days"]) <= 55  # 今日必在本周；3 天前跨周则不计入
    assert "月" in s["week_label"] and "-" in s["week_label"]

    # 归档 → 坚持中消失、已归档出现；恢复
    r = await client.patch(BASE + f"/{pid}", headers=headers, json={"archived": True})
    assert r.status_code == 200
    r = await client.get(BASE, headers=headers)
    assert all(x["id"] != pid for x in r.json()["items"])
    r = await client.get(BASE, headers=headers, params={"archived": "true"})
    assert any(x["id"] == pid for x in r.json()["items"])
    await client.patch(BASE + f"/{pid}", headers=headers, json={"archived": False})

    # 删除 → 404；历史会话的 preset_id 不受影响（悬空）
    r = await client.delete(BASE + f"/{pid}", headers=headers)
    assert r.status_code == 200
    r = await client.get(BASE + f"/{pid}/stats", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_preset_start_inherits_task_and_guard(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "冥想任务"})
    task_id = r.json()["id"]
    r = await client.post(
        BASE,
        headers=headers,
        json={"name": "冥想", "mode": "countdown", "duration_minutes": 10, "task_id": task_id},
    )
    pid = r.json()["id"]

    # 非法 preset 404（先校验，此刻无进行中会话）
    r = await client.post(
        FOCUS, headers=headers, json={"preset_id": "000000000000000000000000"}
    )
    assert r.status_code == 404

    # 预设启动：未显式传 task_id 时沿用预设关联任务
    r = await client.post(FOCUS, headers=headers, json={"preset_id": pid, "planned_minutes": 10})
    assert r.status_code == 200, r.text
    sess = r.json()
    assert sess["preset_id"] == pid and sess["task_id"] == task_id

    # 进行中的会话挡住第二次启动
    r = await client.post(FOCUS, headers=headers, json={"preset_id": pid})
    assert r.status_code == 400

    # 结束会话 → 预设累计
    r = await client.post(FOCUS + f"/{sess['id']}/finish", headers=headers)
    assert r.status_code == 200
    r = await client.get(BASE, headers=headers)
    item = next(x for x in r.json()["items"] if x["id"] == pid)
    assert item["total_seconds"] >= 0

    # 清理
    r = await client.delete(BASE + f"/{pid}", headers=headers)
    assert r.status_code == 200
