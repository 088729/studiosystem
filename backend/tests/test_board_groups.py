import pytest


async def _create_list(client, headers, name):
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


async def _create_task(client, headers, **kwargs):
    payload = {"title": kwargs.pop("title", "任务")}
    payload.update(kwargs)
    r = await client.post("/api/v1/task/tasks", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_board_group_add_with_index(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    lst = await _create_list(client, headers, "位置插入清单")
    post = lambda **kw: client.post(f"/api/v1/task/lists/{lst['id']}/groups", headers=headers, json=kw)

    # 缺省 index = 末尾追加（向后兼容）
    r = await post(name="想要做")
    assert r.status_code == 200, r.text
    r = await post(name="正在做")
    assert r.json()["board_groups"] == ["想要做", "正在做"]

    # 中间位置插入
    r = await post(name="准备做", index=1)
    assert r.status_code == 200, r.text
    assert r.json()["board_groups"] == ["想要做", "准备做", "正在做"]

    # 头部插入
    r = await post(name="想法池", index=0)
    assert r.json()["board_groups"] == ["想法池", "想要做", "准备做", "正在做"]

    # index 越界 clamp：负数→头，超大→尾
    r = await post(name="最前", index=-5)
    assert r.json()["board_groups"][0] == "最前"
    r = await post(name="已完成", index=99)
    assert r.json()["board_groups"][-1] == "已完成"


@pytest.mark.asyncio
async def test_board_group_crud_and_cascade(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    lst = await _create_list(client, headers, "看板清单")

    # 添加分组
    r = await client.post(f"/api/v1/task/lists/{lst['id']}/groups", headers=headers, json={"name": "进行中"})
    assert r.status_code == 200, r.text
    assert r.json()["board_groups"] == ["进行中"]
    r = await client.post(f"/api/v1/task/lists/{lst['id']}/groups", headers=headers, json={"name": "已完成"})
    assert r.json()["board_groups"] == ["进行中", "已完成"]

    # 重名冲突
    r = await client.post(f"/api/v1/task/lists/{lst['id']}/groups", headers=headers, json={"name": "进行中"})
    assert r.status_code == 400

    # 分组内建任务
    task = await _create_task(client, headers, title="分组任务", list_id=lst["id"], group="进行中")
    assert task["group"] == "进行中"

    # 重命名分组级联任务
    r = await client.patch(
        f"/api/v1/task/lists/{lst['id']}/groups",
        headers=headers,
        json={"from_name": "进行中", "to_name": "开发中"},
    )
    assert r.status_code == 200
    assert r.json()["board_groups"] == ["开发中", "已完成"]
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["group"] == "开发中"

    # 删除分组，任务回落未分组
    r = await client.delete(f"/api/v1/task/lists/{lst['id']}/groups/开发中", headers=headers)
    assert r.status_code == 200
    assert r.json()["board_groups"] == ["已完成"]
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["group"] is None


@pytest.mark.asyncio
async def test_board_group_validation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    lst = await _create_list(client, headers, "校验清单")
    await client.post(f"/api/v1/task/lists/{lst['id']}/groups", headers=headers, json={"name": "待办"})

    # 分组不存在 → 400
    r = await client.post(
        "/api/v1/task/tasks", headers=headers, json={"title": "x", "list_id": lst["id"], "group": "不存在"}
    )
    assert r.status_code == 400

    # 收集箱不支持分组 → 400
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "x", "group": "待办"})
    assert r.status_code == 400

    # 看板拖拽换列：PATCH group
    task = await _create_task(client, headers, title="拖我", list_id=lst["id"])
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": "待办"})
    assert r.status_code == 200
    assert r.json()["group"] == "待办"

    # PATCH 到不存在的分组 → 400
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": "没有"})
    assert r.status_code == 400

    # 显式 null 回未分组
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": None})
    assert r.status_code == 200
    assert r.json()["group"] is None


@pytest.mark.asyncio
async def test_board_group_reset_on_move_and_delete_list(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    lst_a = await _create_list(client, headers, "清单A")
    lst_b = await _create_list(client, headers, "清单B")
    await client.post(f"/api/v1/task/lists/{lst_a['id']}/groups", headers=headers, json={"name": "进行中"})

    task = await _create_task(client, headers, title="跨清单", list_id=lst_a["id"], group="进行中")
    assert task["group"] == "进行中"

    # 移动到其他清单 → 分组失效
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}/move", headers=headers, json={"list_id": lst_b["id"]})
    assert r.status_code == 200
    assert r.json()["group"] is None

    # 移回 A 再删清单 → 落收集箱且分组清空
    await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": None})
    await client.patch(f"/api/v1/task/tasks/{task['id']}/move", headers=headers, json={"list_id": lst_a["id"]})
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": "进行中"})
    assert r.status_code == 200
    r = await client.delete(f"/api/v1/task/lists/{lst_a['id']}", headers=headers)
    assert r.status_code == 200
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["list_id"] is None
    assert r.json()["group"] is None


# ---------- 收集箱自定义分组（TaskSettings.inbox_board_groups） ----------


@pytest.mark.asyncio
async def test_inbox_group_crud_and_cascade(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    base = "/api/v1/task/settings/inbox-groups"

    # 添加（含位置插入）
    r = await client.post(base, headers=headers, json={"name": "想要做"})
    assert r.status_code == 200, r.text
    assert r.json()["board_groups"] == ["想要做"]
    r = await client.post(base, headers=headers, json={"name": "正在做"})
    assert r.json()["board_groups"] == ["想要做", "正在做"]
    r = await client.post(base, headers=headers, json={"name": "准备做", "index": 1})
    assert r.json()["board_groups"] == ["想要做", "准备做", "正在做"]

    # 重名 400 / 空名 400
    assert (await client.post(base, headers=headers, json={"name": "想要做"})).status_code == 400
    assert (await client.post(base, headers=headers, json={"name": "  "})).status_code == 400

    # 收集箱任务带分组
    task = await _create_task(client, headers, title="收集箱分组任务", group="准备做")
    assert task["group"] == "准备做"

    # 重命名级联收集箱任务
    r = await client.patch(base, headers=headers, json={"from_name": "准备做", "to_name": "筹备中"})
    assert r.status_code == 200
    assert r.json()["board_groups"] == ["想要做", "筹备中", "正在做"]
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["group"] == "筹备中"

    # 删除分组，任务回落未分组
    r = await client.delete(f"{base}/筹备中", headers=headers)
    assert r.status_code == 200
    assert r.json()["board_groups"] == ["想要做", "正在做"]
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["group"] is None


@pytest.mark.asyncio
async def test_inbox_group_validation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    base = "/api/v1/task/settings/inbox-groups"

    # 收集箱任务：分组不在 inbox_board_groups → 400
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "x", "group": "不存在"})
    assert r.status_code == 400

    await client.post(base, headers=headers, json={"name": "待整理"})

    # PATCH 收集箱任务到合法分组 → 200；非法分组 → 400
    task = await _create_task(client, headers, title="收集箱拖我")
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": "待整理"})
    assert r.status_code == 200
    assert r.json()["group"] == "待整理"
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": "没有"})
    assert r.status_code == 400
    r = await client.patch(f"/api/v1/task/tasks/{task['id']}", headers=headers, json={"group": None})
    assert r.status_code == 200
    assert r.json()["group"] is None

    # 清单任务不受 inbox_board_groups 影响（仍校验清单自己的 board_groups）
    lst = await _create_list(client, headers, "隔离清单")
    r = await client.post(
        "/api/v1/task/tasks", headers=headers, json={"title": "x", "list_id": lst["id"], "group": "待整理"}
    )
    assert r.status_code == 400  # 「待整理」是收集箱分组，不属于该清单

    # 清理：删除收集箱分组，避免影响其他用例
    await client.delete(f"{base}/待整理", headers=headers)
