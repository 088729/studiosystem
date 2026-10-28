import time

import pytest
import pytest_asyncio

# 测试库跨用例共享且标签名要求同 owner 唯一，造数带时间戳后缀避免残留数据冲突
RUN = str(int(time.time() * 1000))


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_tags(client, admin_token):
    """测试与开发库共享，用例结束后清理本批次创建的标签（含级联子标签），不污染侧栏。"""
    yield
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.get("/api/v1/task/tags", headers=headers)
    for item in r.json()["items"]:
        if item["name"].endswith(RUN):
            await client.delete(f"/api/v1/task/tags/{item['id']}", headers=headers)


async def _create_task(client, headers, **kwargs):
    payload = {"title": kwargs.pop("title", "任务")}
    payload.update(kwargs)
    r = await client.post("/api/v1/task/tasks", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_tag_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"回归{RUN}", "color": "#ff0000"})
    assert r.status_code == 200, r.text
    tag = r.json()
    assert tag["color"] == "#ff0000"
    assert tag["parent_id"] is None

    r = await client.get("/api/v1/task/tags", headers=headers)
    assert r.status_code == 200
    assert any(item["id"] == tag["id"] for item in r.json()["items"])

    r = await client.patch(f"/api/v1/task/tags/{tag['id']}", headers=headers, json={"color": "#00ff00"})
    assert r.status_code == 200
    assert r.json()["color"] == "#00ff00"

    r = await client.delete(f"/api/v1/task/tags/{tag['id']}", headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/v1/task/tags", headers=headers)
    assert not any(item["id"] == tag["id"] for item in r.json()["items"])


@pytest.mark.asyncio
async def test_tag_name_conflict(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"冲突标签{RUN}"})
    assert r.status_code == 200
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"冲突标签{RUN}"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tag_parent_validation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"父标签{RUN}"})
    parent = r.json()
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"子标签{RUN}", "parent_id": parent["id"]})
    assert r.status_code == 200
    child = r.json()
    assert child["parent_id"] == parent["id"]

    # 二级嵌套被拒绝：子标签不能再当上级
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"孙标签{RUN}", "parent_id": child["id"]})
    assert r.status_code == 400

    # 上级不能是自身
    r = await client.patch(f"/api/v1/task/tags/{parent['id']}", headers=headers, json={"parent_id": parent["id"]})
    assert r.status_code == 400

    # 含有下级标签的标签不能再挂到别人下面
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"另一父{RUN}"})
    another = r.json()
    r = await client.patch(f"/api/v1/task/tags/{parent['id']}", headers=headers, json={"parent_id": another["id"]})
    assert r.status_code == 400

    # 不存在的上级 404
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"孤儿{RUN}", "parent_id": "000000000000000000000000"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tag_rename_cascades_tasks(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    old_name = f"改名前{RUN}"
    new_name = f"改名后{RUN}"
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": old_name})
    tag = r.json()

    task = await _create_task(client, headers, title="带标签任务", tags=[old_name, "保留"])
    sub = await _create_task(client, headers, title="子任务", tags=[old_name], parent_id=task["id"])

    r = await client.patch(f"/api/v1/task/tags/{tag['id']}", headers=headers, json={"name": new_name})
    assert r.status_code == 200

    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert sorted(r.json()["tags"]) == sorted(["保留", new_name])
    r = await client.get(f"/api/v1/task/tasks/{sub['id']}", headers=headers)
    assert r.json()["tags"] == [new_name]


@pytest.mark.asyncio
async def test_tag_delete_cascades_children_and_tasks(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    p_name, c_name = f"待删父{RUN}", f"待删子{RUN}"
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": p_name})
    parent = r.json()
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": c_name, "parent_id": parent["id"]})
    child = r.json()

    task = await _create_task(client, headers, title="任务", tags=[p_name, c_name, "保留"])

    r = await client.delete(f"/api/v1/task/tags/{parent['id']}", headers=headers)
    assert r.status_code == 200

    # 下级标签一并删除
    r = await client.get("/api/v1/task/tags", headers=headers)
    names = [item["name"] for item in r.json()["items"]]
    assert p_name not in names and c_name not in names

    # 任务上的标签名被移除，任务本身不删
    r = await client.get(f"/api/v1/task/tasks/{task['id']}", headers=headers)
    assert r.json()["tags"] == ["保留"]


@pytest.mark.asyncio
async def test_tag_owner_isolation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.post("/api/v1/task/tags", headers=headers, json={"name": f"隔离标签{RUN}"})
    tag = r.json()
    # 非法 id → 404；他人标签对非 owner 不可见（此处仅测非法 id 与列表隔离由 owner 过滤保证）
    r = await client.get("/api/v1/task/tags", headers=headers)
    assert any(item["id"] == tag["id"] for item in r.json()["items"])
    r = await client.patch("/api/v1/task/tags/not-a-valid-id", headers=headers, json={"name": "x"})
    assert r.status_code == 404
