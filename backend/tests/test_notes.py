import pytest


@pytest.mark.asyncio
async def test_note_list_and_note_task(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 创建笔记清单
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "工作复盘", "kind": "note"})
    assert r.status_code == 200, r.text
    lst = r.json()
    assert lst["kind"] == "note"
    list_id = lst["id"]

    # 非法 kind → 400
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "x", "kind": "bad"})
    assert r.status_code == 400

    # 笔记清单里建任务 → is_note=True（跟随清单 kind）
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "9月第2周工作总结", "list_id": list_id})
    assert r.status_code == 200, r.text
    note = r.json()
    assert note["is_note"] is True
    assert note["status"] == "todo"

    # 任务清单里建任务 → is_note=False
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "普通清单"})
    task_list_id = r.json()["id"]
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "普通任务", "list_id": task_list_id})
    assert r.json()["is_note"] is False

    # 收集箱任务 → is_note=False
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "收集箱任务"})
    assert r.json()["is_note"] is False

    # 显式 is_note 优先于清单 kind
    r = await client.post(
        "/api/v1/task/tasks", headers=headers, json={"title": "显式笔记", "list_id": task_list_id, "is_note": True}
    )
    assert r.json()["is_note"] is True


@pytest.mark.asyncio
async def test_note_conversion(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 任务 → 笔记
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "可转换"})
    t = r.json()
    r = await client.patch(f"/api/v1/task/tasks/{t['id']}", headers=headers, json={"is_note": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_note"] is True

    # 笔记 → 任务
    r = await client.patch(f"/api/v1/task/tasks/{t['id']}", headers=headers, json={"is_note": False})
    assert r.json()["is_note"] is False

    # 含子任务的任务不可转笔记 → 400
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "父任务"})
    parent = r.json()
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "子任务", "parent_id": parent["id"]})
    assert r.status_code == 200, r.text
    r = await client.patch(f"/api/v1/task/tasks/{parent['id']}", headers=headers, json={"is_note": True})
    assert r.status_code == 400

    # 清单 kind 切换 + 列表返回 kind
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "K"})
    lid = r.json()["id"]
    r = await client.patch(f"/api/v1/task/lists/{lid}", headers=headers, json={"kind": "note"})
    assert r.json()["kind"] == "note"
    r = await client.get("/api/v1/task/lists", headers=headers)
    kinds = {x["id"]: x["kind"] for x in r.json()["items"]}
    assert kinds[lid] == "note"

    await client.delete(f"/api/v1/task/tasks/{t['id']}", headers=headers)
    await client.delete(f"/api/v1/task/tasks/{parent['id']}", headers=headers)
