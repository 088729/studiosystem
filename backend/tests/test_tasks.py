from datetime import datetime, timedelta, timezone

import pytest


async def _create_task(client, headers, **kwargs):
    payload = {"title": kwargs.pop("title", "任务")}
    payload.update(kwargs)
    r = await client.post("/api/v1/task/tasks", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_list_crud_and_delete_falls_to_inbox(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "工作", "color": "#ff0000"})
    assert r.status_code == 200
    list_id = r.json()["id"]
    assert r.json()["color"] == "#ff0000"

    r = await client.get("/api/v1/task/lists", headers=headers)
    assert r.status_code == 200
    assert any(item["id"] == list_id for item in r.json()["items"])

    r = await client.patch(f"/api/v1/task/lists/{list_id}", headers=headers, json={"name": "工作2"})
    assert r.status_code == 200
    assert r.json()["name"] == "工作2"

    task = await _create_task(client, headers, title="清单内任务", list_id=list_id)
    assert task["list_id"] == list_id

    r = await client.delete(f"/api/v1/task/lists/{list_id}", headers=headers)
    assert r.status_code == 200

    # 任务落收集箱（list_id 置 null），不被删除
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["list_id"] is None


@pytest.mark.asyncio
async def test_task_crud_and_complete_idempotent(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    task = await _create_task(client, headers, title="写周报", priority=3, tags=["P0"])
    assert task["status"] == "todo"
    assert task["priority"] == 3

    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"note": "周五前"})
    assert r.status_code == 200
    assert r.json()["note"] == "周五前"

    # 完成
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    first_completed_at = r.json()["completed_at"]
    assert first_completed_at is not None

    # 幂等：重复完成不改写 completed_at
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    assert r.status_code == 200
    assert r.json()["completed_at"] == first_completed_at

    # 取消完成
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": False})
    assert r.json()["status"] == "todo"
    assert r.json()["completed_at"] is None

    # 软删除后查询不到
    r = await client.delete(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.status_code == 200
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.status_code == 404
    r = await client.get("/api/v1/task/tasks?smart=all", headers=headers)
    assert all(item["id"] != task["id"] for item in r.json()["items"])


@pytest.mark.asyncio
async def test_smart_today_includes_overdue(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    overdue = await _create_task(client, headers, title="逾期任务", due_at=yesterday)
    future = await _create_task(
        client, headers, title="远期任务",
        due_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    )
    done_overdue = await _create_task(client, headers, title="已完成的逾期", due_at=yesterday)
    await client.post(f"/api/v1/task/tasks/{done_overdue['id']}/complete", headers=headers, json={"done": True})
    done_today = await _create_task(
        client, headers, title="已完成的今日",
        # 用 +08:00 当地正午（与查询的 tz_offset_minutes=480 对齐），避免 UTC 日期 ≠ 本地日期时跨界失败
        due_at=datetime.now(timezone(timedelta(hours=8))).replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
    )
    await client.post(f"/api/v1/task/tasks/{done_today['id']}/complete", headers=headers, json={"done": True})

    # 按 due_at 升序且 limit 上限 200：逾期任务多时本任务可能落在首页之外，翻页找全
    ids = []
    offset = 0
    while True:
        r = await client.get(
            f"/api/v1/task/tasks?smart=today&tz_offset_minutes=480&limit=200&offset={offset}",
            headers=headers,
        )
        items = r.json()["items"]
        ids += [item["id"] for item in items]
        if len(items) < 200:
            break
        offset += 200
    assert overdue["id"] in ids          # 逾期任务出现在「今天」
    assert future["id"] not in ids
    assert done_overdue["id"] not in ids  # 已完成的逾期不出现
    assert done_today["id"] in ids        # 今日到期的已完成保留在「已完成」分组

    r = await client.get("/api/v1/task/tasks?smart=completed", headers=headers)
    assert any(item["id"] == done_overdue["id"] for item in r.json()["items"])


@pytest.mark.asyncio
async def test_list_id_and_smart_conflict(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.get("/api/v1/task/tasks?list_id=abc&smart=today", headers=headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_owner_isolation(client, admin_token):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 造一个 tester 用户
    r = await client.post(
        "/api/v1/common/auth/users", headers=admin_headers,
        json={"username": "task_tester", "password": "pass12345", "role_name": "tester"},
    )
    assert r.status_code in (200, 400), r.text
    r = await client.post("/api/v1/common/auth/login", json={"username": "task_tester", "password": "pass12345"})
    assert r.status_code == 200, r.text
    tester_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    task = await _create_task(client, admin_headers, title="admin 的私有任务")

    # tester 看不到 admin 的任务
    r = await client.get("/api/v1/task/tasks?smart=all", headers=tester_headers)
    assert r.status_code == 200
    assert all(item["id"] != task["id"] for item in r.json()["items"])
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=tester_headers)
    assert r.status_code == 404

    # viewer 无新建权限
    r = await client.post(
        "/api/v1/common/auth/users", headers=admin_headers,
        json={"username": "task_viewer", "password": "pass12345", "role_name": "viewer"},
    )
    assert r.status_code in (200, 400), r.text
    r = await client.post("/api/v1/common/auth/login", json={"username": "task_viewer", "password": "pass12345"})
    viewer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.post("/api/v1/task/tasks", headers=viewer_headers, json={"title": "越权"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_subtask_rules(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    parent = await _create_task(client, headers, title="父任务")
    sub = await _create_task(client, headers, title="子任务", parent_id=parent["id"])
    assert sub["parent_id"] == parent["id"]

    # 只允许一级子任务
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "孙任务", "parent_id": sub["id"]})
    assert r.status_code == 400

    # 子任务不进智能清单
    r = await client.get("/api/v1/task/tasks?smart=all", headers=headers)
    assert all(item["id"] != sub["id"] for item in r.json()["items"])

    # 父任务详情含子任务与进度
    r = await client.get(f"/api/v1/task/tasks/{parent['id']}", headers=headers)
    assert r.json()["subtask_total"] == 1
    assert r.json()["subtask_done"] == 0
    assert r.json()["subtasks"][0]["id"] == sub["id"]

    # 软删父任务级联软删子任务
    await client.delete(f"/api/v1/task/tasks/{parent['id']}", headers=headers)
    r = await client.get(f"/api/v1/task/tasks/{sub['id']}", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_drag_convert_to_subtask(client, admin_token):
    """拖动转子任务（对齐主流待办应用）：PATCH parent_id 转换/校验/转回"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    parent = await _create_task(client, headers, title="父任务P")
    child = await _create_task(client, headers, title="待转换C")

    # 普通任务 → 子任务：parent_id 落库、list_id 跟随父任务、从列表消失、父任务计数+1
    r = await client.patch(f"/api/v1/task/tasks/{child['id']}", headers=headers, json={"parent_id": parent["id"]})
    assert r.status_code == 200
    assert r.json()["parent_id"] == parent["id"]
    assert r.json()["list_id"] == parent["list_id"]
    r = await client.get("/api/v1/task/tasks?smart=all", headers=headers)
    assert all(item["id"] != child["id"] for item in r.json()["items"])
    r = await client.get(f"/api/v1/task/tasks/{parent['id']}", headers=headers)
    assert r.json()["subtask_total"] == 1

    # 转回普通任务（显式 null）：回到列表
    r = await client.patch(f"/api/v1/task/tasks/{child['id']}", headers=headers, json={"parent_id": None})
    assert r.status_code == 200
    assert r.json()["parent_id"] is None
    r = await client.get("/api/v1/task/tasks?smart=all", headers=headers)
    assert any(item["id"] == child["id"] for item in r.json()["items"])

    # 不能转为自己的子任务
    r = await client.patch(f"/api/v1/task/tasks/{child['id']}", headers=headers, json={"parent_id": child["id"]})
    assert r.status_code == 400

    # 不能转为子任务的子任务（只允许一级）
    sub2 = await _create_task(client, headers, title="子任务S", parent_id=parent["id"])
    r = await client.patch(f"/api/v1/task/tasks/{child['id']}", headers=headers, json={"parent_id": sub2["id"]})
    assert r.status_code == 400

    # 含子任务的任务不能转为子任务
    r = await client.patch(f"/api/v1/task/tasks/{parent['id']}", headers=headers, json={"parent_id": child["id"]})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_move_cascades_subtasks_and_subtask_move_guard(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "目标清单"})
    target_list = r.json()["id"]

    parent = await _create_task(client, headers, title="父任务A")
    sub = await _create_task(client, headers, title="子任务A", parent_id=parent["id"])

    # 子任务不能单独移动
    r = await client.patch(f"/api/v1/task/tasks/{sub['id']}/move", headers=headers, json={"list_id": target_list})
    assert r.status_code == 400

    # 移动父任务，子任务 list_id 级联同步
    r = await client.patch(f"/api/v1/task/tasks/{parent['id']}/move", headers=headers, json={"list_id": target_list})
    assert r.status_code == 200
    assert r.json()["list_id"] == target_list
    r = await client.get(f"/api/v1/task/tasks/{sub['id']}", headers=headers)
    assert r.json()["list_id"] == target_list


@pytest.mark.asyncio
async def test_sort_before_and_subtask_order_increment(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    t1 = await _create_task(client, headers, title="排序1")
    t2 = await _create_task(client, headers, title="排序2")
    assert t2["sort_order"] > t1["sort_order"]

    # t2 插到 t1 前面
    r = await client.patch(
        f"/api/v1/task/tasks/{t2['id']}/sort", headers=headers,
        json={"before_task_id": t1["id"]},
    )
    assert r.status_code == 200
    assert r.json()["sort_order"] < t1["sort_order"]

    # 子任务 sort_order 在兄弟间递增
    parent = await _create_task(client, headers, title="排序父")
    s1 = await _create_task(client, headers, title="子1", parent_id=parent["id"])
    s2 = await _create_task(client, headers, title="子2", parent_id=parent["id"])
    assert s2["sort_order"] > s1["sort_order"]

    # 子任务排序：s2 插到 s1 前
    r = await client.patch(
        f"/api/v1/task/tasks/{s2['id']}/sort", headers=headers,
        json={"before_task_id": s1["id"]},
    )
    assert r.status_code == 200
    assert r.json()["sort_order"] < s1["sort_order"]


@pytest.mark.asyncio
async def test_tag_and_search_filter(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    tagged = await _create_task(client, headers, title="带标签任务", tags=["回归", "P0"])
    await _create_task(client, headers, title="无标签任务")

    r = await client.get("/api/v1/task/tasks?smart=all&tag=回归", headers=headers)
    ids = [item["id"] for item in r.json()["items"]]
    assert tagged["id"] in ids

    r = await client.get("/api/v1/task/tasks?smart=all&q=带标签", headers=headers)
    assert any(item["id"] == tagged["id"] for item in r.json()["items"])
    assert all("带标签" in item["title"] for item in r.json()["items"])


# ---------- P2：重复任务与提醒 ----------

@pytest.mark.asyncio
async def test_recurrence_daily_reset(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    due = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0) + timedelta(days=1)

    task = await _create_task(
        client, headers, title="每日站会",
        due_at=due.isoformat(),
        recurrence={"freq": "daily", "interval": 1},
    )
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    body = r.json()
    # 重置为下一实例：status 回 todo、due_at 顺移一天、计数 +1
    assert body["status"] == "todo"
    assert body["completed_at"] is None
    next_due = datetime.fromisoformat(body["due_at"].replace("Z", "+00:00"))
    if next_due.tzinfo is None:
        next_due = next_due.replace(tzinfo=timezone.utc)
    assert abs((next_due - (due + timedelta(days=1))).total_seconds()) < 60
    assert body["recurrence"]["occurrences_completed"] == 1


@pytest.mark.asyncio
async def test_recurrence_after_count_stops(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    due = datetime.now(timezone.utc) + timedelta(days=1)

    task = await _create_task(
        client, headers, title="只做一次",
        due_at=due.isoformat(),
        recurrence={"freq": "daily", "end_type": "after_count", "count": 1},
    )
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    body = r.json()
    # 达到次数上限：保持 done，不再生成
    assert body["status"] == "done"
    assert body["recurrence"]["occurrences_completed"] == 1


@pytest.mark.asyncio
async def test_recurrence_resets_subtasks(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    due = datetime.now(timezone.utc) + timedelta(days=1)

    parent = await _create_task(
        client, headers, title="每日检查",
        due_at=due.isoformat(),
        recurrence={"freq": "daily"},
    )
    sub = await _create_task(client, headers, title="检查项", parent_id=parent["id"])
    await client.post(f"/api/v1/task/tasks/{sub['id']}/complete", headers=headers, json={"done": True})

    await client.post(f"/api/v1/task/tasks/{parent['id']}/complete", headers=headers, json={"done": True})
    r = await client.get(f"/api/v1/task/tasks/{sub['id']}", headers=headers)
    assert r.json()["status"] == "todo"
    assert r.json()["completed_at"] is None


@pytest.mark.asyncio
async def test_recurrence_month_end_clamp(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    task = await _create_task(
        client, headers, title="月末任务",
        due_at="2026-01-31T09:00:00+00:00",
        recurrence={"freq": "monthly"},
    )
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    next_due = datetime.fromisoformat(r.json()["due_at"].replace("Z", "+00:00"))
    if next_due.tzinfo is None:
        next_due = next_due.replace(tzinfo=timezone.utc)
    # 1/31 → clamp 到 2 月最后一天
    assert next_due.month == 2 and next_due.day == 28


@pytest.mark.asyncio
async def test_reminder_scan_and_ack(client, admin_token):
    from app.services.task.reminder_loop import scan_due_reminders

    headers = {"Authorization": f"Bearer {admin_token}"}
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    task = await _create_task(client, headers, title="到点提醒", reminders=[{"at": past}])
    done_task = await _create_task(client, headers, title="已完成任务的提醒", reminders=[{"at": past}])
    await client.post(f"/api/v1/task/tasks/{done_task['id']}/complete", headers=headers, json={"done": True})

    hit = await scan_due_reminders()
    assert hit >= 1

    # 已完成任务的提醒不触发
    r = await client.get(f"/api/v1/task/tasks/{done_task['id']}", headers=headers)
    assert r.json()["reminders"][0]["triggered"] is False

    # pending-reminders 包含待消费提醒
    r = await client.get("/api/v1/task/views/pending-reminders", headers=headers)
    ids = [item["task_id"] for item in r.json()["items"]]
    assert task["id"] in ids
    assert done_task["id"] not in ids

    # ack 后从 pending 消失
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/reminders/ack", headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/v1/task/views/pending-reminders", headers=headers)
    assert all(item["task_id"] != task["id"] for item in r.json()["items"])


async def test_persistent_reminder_roundtrip(client, admin_token):
    """持续提醒开关：创建/更新落库，pending-reminders 带 persistent 标记。"""
    from app.services.task.reminder_loop import scan_due_reminders

    headers = {"Authorization": f"Bearer {admin_token}"}
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    task = await _create_task(
        client, headers, title="持续提醒", reminders=[{"at": past}], persistent_reminder=True
    )
    assert task["persistent_reminder"] is True

    await scan_due_reminders()
    r = await client.get("/api/v1/task/views/pending-reminders", headers=headers)
    item = next((i for i in r.json()["items"] if i["task_id"] == task["id"]), None)
    assert item and item["persistent"] is True

    # 关闭后 pending 标记为 False
    r = await client.patch(
        f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"persistent_reminder": False}
    )
    assert r.status_code == 200 and r.json()["persistent_reminder"] is False
    r = await client.get("/api/v1/task/views/pending-reminders", headers=headers)
    item = next((i for i in r.json()["items"] if i["task_id"] == task["id"]), None)
    assert item and item["persistent"] is False


# ---------- P3：日历 / 统计 / 用例联动 / assignee ----------

@pytest.mark.asyncio
async def test_calendar_view(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    now = datetime.now(timezone.utc)

    todo_task = await _create_task(client, headers, title="日历待办", due_at=now.isoformat())
    done_task = await _create_task(client, headers, title="日历已完成", due_at=now.isoformat())
    await client.post(f"/api/v1/task/tasks/{done_task['id']}/complete", headers=headers, json={"done": True})
    parent = await _create_task(client, headers, title="日历父任务", due_at=now.isoformat())
    sub = await _create_task(client, headers, title="日历子任务", parent_id=parent["id"], due_at=now.isoformat())
    out_task = await _create_task(
        client, headers, title="区间外任务",
        due_at=(now + timedelta(days=60)).isoformat(),
    )

    start = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = await client.get(f"/api/v1/task/views/calendar?start={start}&end={end}", headers=headers)
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert todo_task["id"] in ids      # todo 上日历
    assert done_task["id"] in ids      # done 也上日历（前端划线）
    assert sub["id"] not in ids        # 子任务不上日历
    assert out_task["id"] not in ids   # 区间外不出现


@pytest.mark.asyncio
async def test_summary(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    now = datetime.now(timezone.utc)

    await _create_task(client, headers, title="统计逾期", due_at=(now - timedelta(days=2)).isoformat())
    today_task = await _create_task(client, headers, title="统计今日", due_at=now.isoformat())
    done_task = await _create_task(client, headers, title="统计完成", due_at=now.isoformat())
    await client.post(f"/api/v1/task/tasks/{done_task['id']}/complete", headers=headers, json={"done": True})

    r = await client.get("/api/v1/task/views/summary?tz_offset_minutes=480", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["overdue"] >= 1
    assert body["today_todo"] >= 2      # 逾期 + 今日
    assert body["completed_total"] >= 1


@pytest.mark.asyncio
async def test_case_ref_and_soft_unlink_on_map_delete(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 建导图（默认根节点 uid=root，文本=标题）
    r = await client.post("/api/v1/case/maps", headers=headers, json={"title": "支付模块导图"})
    assert r.status_code == 200
    map_id = r.json()["id"]

    task = await _create_task(
        client, headers, title="联动任务",
        case_map_id=map_id, case_node_id="root",
    )
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    body = r.json()
    assert body["case_map_title"] == "支付模块导图"
    assert body["case_node_text"] == "支付模块导图"  # 根节点文本 = 导图标题

    # 删除导图后任务引用置 null，任务本身保留
    r = await client.delete(f"/api/v1/case/maps/{map_id}", headers=headers)
    assert r.status_code == 200
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["case_map_id"] is None
    assert r.json()["case_map_title"] is None


@pytest.mark.asyncio
async def test_assignee_validation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tasks", headers=headers,
                          json={"title": "分配任务", "assignee": "不存在的人"})
    assert r.status_code == 400

    task = await _create_task(client, headers, title="分配任务", assignee="task_tester")
    assert task["assignee"] == "task_tester"

    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"assignee": None})
    assert r.status_code == 200
    assert r.json()["assignee"] is None


@pytest.mark.asyncio
async def test_task_pin_roundtrip(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    task = await _create_task(client, headers, title="置顶任务")
    assert task["is_pinned"] is False  # 默认不置顶

    # 置顶
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"is_pinned": True})
    assert r.status_code == 200
    assert r.json()["is_pinned"] is True

    # 详情返回 is_pinned
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["is_pinned"] is True

    # 列表返回 is_pinned
    r = await client.get("/api/v1/task/tasks?smart=all", headers=headers)
    item = next(i for i in r.json()["items"] if i["id"] == task["id"])
    assert item["is_pinned"] is True

    # 取消置顶（部分更新不影响其他字段）
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"is_pinned": False})
    assert r.status_code == 200
    assert r.json()["is_pinned"] is False
    assert r.json()["title"] == "置顶任务"


@pytest.mark.asyncio
async def test_batch_tags(client, admin_token):
    """批量加标签：并集合并、不移除已有、不重复。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    t1 = await _create_task(client, headers, title="批量标签A", tags=["已有"])
    t2 = await _create_task(client, headers, title="批量标签B")

    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"], t2["id"]], "action": "tags", "payload": {"tags": ["回归", "P0"]}},
    )
    assert r.status_code == 200
    assert r.json()["ok"] == 2
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    assert r.json()["tags"] == ["已有", "回归", "P0"]
    r = await client.get(f"/api/v1/task/tasks/{t2['id']}", headers=headers)
    assert r.json()["tags"] == ["回归", "P0"]

    # 重复加同一标签不产生重复项
    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"]], "action": "tags", "payload": {"tags": ["回归"]}},
    )
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    assert r.json()["tags"] == ["已有", "回归", "P0"]


@pytest.mark.asyncio
async def test_batch_due_with_reminders(client, admin_token):
    """批量「日期与提醒」：payload 带非空 reminders 时整体替换；不带则保留原提醒；清日期时连提醒一起清。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    t1 = await _create_task(client, headers, title="批量提醒A")
    # 原有提醒，批量设日期不带 reminders → 保留
    r = await client.patch(
        f"/api/v1/task/tasks/{t1['id']}",
        headers=headers,
        json={"reminders": [{"at": "2030-01-01T09:00:00+08:00"}]},
    )
    assert r.status_code == 200
    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"]], "action": "due", "payload": {"due_at": "2030-02-01T16:00:00+00:00", "all_day": True, "reminders": []}},
    )
    assert r.json()["ok"] == 1
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    assert len(r.json()["reminders"]) == 1  # 空 reminders 不动旧提醒

    # 带 reminders → 整体替换
    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={
            "ids": [t1["id"]],
            "action": "due",
            "payload": {
                "due_at": "2030-03-01T16:00:00+00:00",
                "all_day": True,
                "reminders": [{"at": "2030-03-02T09:00:00+08:00"}, {"at": "2030-03-03T09:00:00+08:00"}],
                "persistent_reminder": True,
            },
        },
    )
    assert r.json()["ok"] == 1
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    body = r.json()
    assert len(body["reminders"]) == 2
    assert body["reminders"][0]["triggered"] is False  # Reminder 默认值补全（勿裸 dict）
    assert body["persistent_reminder"] is True

    # 清日期 → 提醒/持续提醒一并清
    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"]], "action": "due", "payload": {"due_at": None, "all_day": True}},
    )
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    body = r.json()
    assert body["due_at"] is None
    assert body["reminders"] == []
    assert body["persistent_reminder"] is False


@pytest.mark.asyncio
async def test_batch_pin(client, admin_token):
    """批量置顶/取消置顶（对齐主流待办应用桌面端批量操作面板的「置顶」）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    t1 = await _create_task(client, headers, title="批量置顶A")
    t2 = await _create_task(client, headers, title="批量置顶B")

    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"], t2["id"]], "action": "pin", "payload": {"pinned": True}},
    )
    assert r.status_code == 200
    assert r.json()["ok"] == 2
    for t in (t1, t2):
        r = await client.get(f"/api/v1/task/tasks/{t['id']}", headers=headers)
        assert r.json()["is_pinned"] is True

    # 批量取消置顶
    r = await client.post(
        "/api/v1/task/tasks/batch",
        headers=headers,
        json={"ids": [t1["id"]], "action": "pin", "payload": {"pinned": False}},
    )
    assert r.json()["ok"] == 1
    r = await client.get(f"/api/v1/task/tasks/{t1['id']}", headers=headers)
    assert r.json()["is_pinned"] is False


# ---------- P2：时间段（start_at）/ 重复任务补充 ----------

@pytest.mark.asyncio
async def test_time_range_roundtrip(client, admin_token):
    """时间段任务：start_at + duration_minutes 创建/编辑/返回；all_day 语义不变。"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    start = datetime.now(timezone.utc).replace(microsecond=0)
    due = start + timedelta(hours=1)
    task = await _create_task(
        client, headers, title="评审会议",
        start_at=start.isoformat(), due_at=due.isoformat(), duration_minutes=60,
    )
    assert task["duration_minutes"] == 60
    got_start = datetime.fromisoformat(task["start_at"].replace("Z", "+00:00"))
    if got_start.tzinfo is None:
        got_start = got_start.replace(tzinfo=timezone.utc)
    assert abs((got_start - start).total_seconds()) < 1

    # 编辑 start_at
    new_start = start + timedelta(days=1)
    r = await client.patch(
        f"/api/v1/task/tasks/{task['id']}", headers=headers,
        json={"start_at": new_start.isoformat(), "duration_minutes": 90},
    )
    assert r.status_code == 200
    assert r.json()["duration_minutes"] == 90
    got_start = datetime.fromisoformat(r.json()["start_at"].replace("Z", "+00:00"))
    if got_start.tzinfo is None:
        got_start = got_start.replace(tzinfo=timezone.utc)
    assert abs((got_start - new_start).total_seconds()) < 1

    # 详情返回 start_at
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["start_at"] is not None


@pytest.mark.asyncio
async def test_recurrence_by_date_stops_and_reminders_reset(client, admin_token):
    """by_date 结束条件：下一次超过 end_date 保持 done；未超期时 reminders 触发标记复位。"""
    from app.services.task.reminder_loop import scan_due_reminders

    headers = {"Authorization": f"Bearer {admin_token}"}
    due = datetime.now(timezone.utc) + timedelta(days=1)
    end_date = (due + timedelta(hours=12)).isoformat()  # 下一次（+1天）超过 end_date

    task = await _create_task(
        client, headers, title="截止前每日",
        due_at=due.isoformat(),
        recurrence={"freq": "daily", "end_type": "by_date", "end_date": end_date},
    )
    r = await client.post(f"/api/v1/task/tasks/{task['id']}/complete", headers=headers, json={"done": True})
    body = r.json()
    assert body["status"] == "done"  # 下一次超过 end_date：不再重置
    assert body["recurrence"]["occurrences_completed"] == 1

    # 未超期：重置后 reminders 触发标记一并复位
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    task2 = await _create_task(
        client, headers, title="带提醒的每日任务",
        due_at=due.isoformat(), reminders=[{"at": past}],
        recurrence={"freq": "daily"},
    )
    await scan_due_reminders()
    r = await client.get(f"/api/v1/task/tasks/{task2['id']}", headers=headers)
    assert r.json()["reminders"][0]["triggered"] is True

    r = await client.post(f"/api/v1/task/tasks/{task2['id']}/complete", headers=headers, json={"done": True})
    body = r.json()
    assert body["status"] == "todo"  # 已重置为下一实例
    assert body["reminders"][0]["triggered"] is False
    assert body["reminders"][0]["notified"] is False


@pytest.mark.asyncio
async def test_list_icon_roundtrip(client, admin_token):
    """清单图标字段（对齐主流待办应用图标）：创建/更新/读取全链路。"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(
        "/api/v1/task/lists", headers=headers,
        json={"name": "图标清单", "color": "#ff0000", "icon": "briefcase"},
    )
    assert r.status_code == 200, r.text
    list_id = r.json()["id"]
    assert r.json()["icon"] == "briefcase"

    r = await client.get("/api/v1/task/lists", headers=headers)
    assert any(item["id"] == list_id and item["icon"] == "briefcase" for item in r.json()["items"])

    # 更新图标 / 清除图标
    r = await client.patch(f"/api/v1/task/lists/{list_id}", headers=headers, json={"icon": "heart"})
    assert r.json()["icon"] == "heart"
    r = await client.patch(f"/api/v1/task/lists/{list_id}", headers=headers, json={"icon": None})
    assert r.json()["icon"] is None

    # 不设图标的旧行为：icon 为 null
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "无图标清单"})
    assert r.json()["icon"] is None
    await client.delete(f"/api/v1/task/lists/{r.json()['id']}", headers=headers)

    await client.delete(f"/api/v1/task/lists/{list_id}", headers=headers)
