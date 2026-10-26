"""协作共享清单 + 评论测试。

场景：admin 创建清单共享给 bob，bob 可看/建任务；viewer 不可勾选/改删，升为 editor 后可勾选，双方可评论。
"""
import pytest


async def _login(client, username, password):
    r = await client.post("/api/v1/common/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
async def bob_headers(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.post(
        "/api/v1/common/auth/users",
        headers=headers,
        json={"username": "bob", "password": "bob12345", "role_name": "tester"},
    )
    if r.status_code == 400 and "已存在" in r.text:
        pass  # 已存在则直接登录
    else:
        assert r.status_code == 200, r.text
    token = await _login(client, "bob", "bob12345")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_share_flow(client, admin_token, bob_headers):
    admin = {"Authorization": f"Bearer {admin_token}"}
    bob = bob_headers

    # admin 创建清单
    r = await client.post("/api/v1/task/lists", headers=admin, json={"name": "共享清单"})
    list_id = r.json()["id"]

    # bob 尚不可见
    r = await client.get(f"/api/v1/task/tasks?list_id={list_id}", headers=bob)
    assert r.status_code == 404

    # admin 添加 bob 为成员
    r = await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=admin, json={"username": "bob"})
    assert r.status_code == 200, r.text
    assert any(m["username"] == "bob" and m["role"] == "viewer" for m in r.json()["items"])

    # 重复添加幂等
    r = await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=admin, json={"username": "bob"})
    assert [m["username"] for m in r.json()["items"]].count("bob") == 1

    # 添加不存在用户 → 400
    r = await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=admin, json={"username": "nobody"})
    assert r.status_code == 400

    # bob 的清单列表包含共享清单且标记 is_shared
    r = await client.get("/api/v1/task/lists", headers=bob)
    shared = [i for i in r.json()["items"] if i["id"] == list_id]
    assert len(shared) == 1 and shared[0]["is_shared"] is True

    # admin 的列表中该清单 is_shared=False
    r = await client.get("/api/v1/task/lists", headers=admin)
    own = next(i for i in r.json()["items"] if i["id"] == list_id)
    assert own["is_shared"] is False
    assert any(m["username"] == "bob" for m in own["members"])


@pytest.mark.asyncio
async def test_shared_task_visibility_and_permissions(client, admin_token, bob_headers):
    admin = {"Authorization": f"Bearer {admin_token}"}
    bob = bob_headers

    r = await client.post("/api/v1/task/lists", headers=admin, json={"name": "协作执行"})
    list_id = r.json()["id"]
    await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=admin, json={"username": "bob"})

    # admin 在共享清单建任务
    r = await client.post("/api/v1/task/tasks", headers=admin, json={"title": "回归支付", "list_id": list_id})
    task_id = r.json()["id"]

    # bob 通过 list_id 查询可见；smart=all（owner 隔离）不可见
    r = await client.get(f"/api/v1/task/tasks?list_id={list_id}", headers=bob)
    assert any(t["id"] == task_id for t in r.json()["items"])
    r = await client.get("/api/v1/task/tasks?smart=all", headers=bob)
    assert all(t["id"] != task_id for t in r.json()["items"])

    # bob 详情可见；默认 viewer 角色不可勾选完成（B2 收紧：viewer 只读）
    r = await client.get(f"/api/v1/task/tasks/{task_id}", headers=bob)
    assert r.status_code == 200
    r = await client.post(f"/api/v1/task/tasks/{task_id}/complete", headers=bob, json={"done": True})
    assert r.status_code == 404

    # admin 将 bob 升为 editor 后可勾选完成
    r = await client.patch(
        f"/api/v1/task/share/lists/{list_id}/members/bob", headers=admin, json={"role": "editor"}
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/task/tasks/{task_id}/complete", headers=bob, json={"done": True})
    assert r.status_code == 200
    assert r.json()["status"] == "done"

    # bob 不能编辑/删除/移动（tester 角色无 task:edit/delete → 403；有权限时服务层可见性 → 404）
    r = await client.patch(f"/api/v1/task/tasks/{task_id}", headers=bob, json={"note": "x"})
    assert r.status_code in (403, 404)
    r = await client.delete(f"/api/v1/task/tasks/{task_id}", headers=bob)
    assert r.status_code in (403, 404)
    r = await client.patch(f"/api/v1/task/tasks/{task_id}/move", headers=bob, json={"list_id": None})
    assert r.status_code in (403, 404)

    # bob 可在共享清单建任务（owner=bob）；但 tester 无 task:edit，bob 改自己的任务也会 403，跳过编辑断言
    r = await client.post("/api/v1/task/tasks", headers=bob, json={"title": "bob的任务", "list_id": list_id})
    assert r.status_code == 200
    bob_task = r.json()
    assert bob_task["owner"] == "bob"
    # admin（清单 owner）也能看到 bob 建的任务
    r = await client.get(f"/api/v1/task/tasks?list_id={list_id}", headers=admin)
    assert any(t["id"] == bob_task["id"] for t in r.json()["items"])

    # bob 不能管理成员（403）
    r = await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=bob, json={"username": "x"})
    assert r.status_code == 403

    # 移除成员后 bob 立即不可见
    r = await client.delete(f"/api/v1/task/share/lists/{list_id}/members/bob", headers=admin)
    assert r.status_code == 200
    r = await client.get(f"/api/v1/task/tasks?list_id={list_id}", headers=bob)
    assert r.status_code == 404
    r = await client.get(f"/api/v1/task/tasks/{task_id}", headers=bob)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_comments(client, admin_token, bob_headers):
    admin = {"Authorization": f"Bearer {admin_token}"}
    bob = bob_headers

    r = await client.post("/api/v1/task/lists", headers=admin, json={"name": "评论清单"})
    list_id = r.json()["id"]
    r = await client.post("/api/v1/task/tasks", headers=admin, json={"title": "评论任务", "list_id": list_id})
    task_id = r.json()["id"]

    # 未共享时 bob 不能评论（任务不可见 → 404）
    r = await client.post(f"/api/v1/task/tasks/{task_id}/comments", headers=bob, json={"content": "hi"})
    assert r.status_code == 404

    await client.post(f"/api/v1/task/share/lists/{list_id}/members", headers=admin, json={"username": "bob"})

    r = await client.post(f"/api/v1/task/tasks/{task_id}/comments", headers=admin, json={"content": "请尽快回归"})
    assert r.status_code == 200
    r = await client.post(f"/api/v1/task/tasks/{task_id}/comments", headers=bob, json={"content": "收到"})
    assert r.status_code == 200
    bob_comment_id = r.json()["id"]

    r = await client.get(f"/api/v1/task/tasks/{task_id}/comments", headers=bob)
    assert len(r.json()["items"]) == 2

    # bob 删自己的评论
    r = await client.delete(f"/api/v1/task/comments/{bob_comment_id}", headers=bob)
    assert r.status_code == 200

    # 清单 owner（admin）可删他人评论
    r = await client.post(f"/api/v1/task/tasks/{task_id}/comments", headers=bob, json={"content": "再评"})
    cid = r.json()["id"]
    r = await client.delete(f"/api/v1/task/comments/{cid}", headers=admin)
    assert r.status_code == 200

    # 编辑：仅作者本人可编辑
    r = await client.post(f"/api/v1/task/tasks/{task_id}/comments", headers=bob, json={"content": "原文"})
    cid = r.json()["id"]
    r = await client.patch(f"/api/v1/task/comments/{cid}", headers=admin, json={"content": "admin改"})
    assert r.status_code == 403
    r = await client.patch(f"/api/v1/task/comments/{cid}", headers=bob, json={"content": "改后"})
    assert r.status_code == 200
    assert r.json()["content"] == "改后"
    r = await client.get(f"/api/v1/task/tasks/{task_id}/comments", headers=bob)
    assert any(c["id"] == cid and c["content"] == "改后" for c in r.json()["items"])


@pytest.mark.asyncio
async def test_share_users_endpoint(client, admin_token, bob_headers):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await client.get("/api/v1/task/share/users", headers=headers)
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()["items"]]
    assert "admin" in usernames and "bob" in usernames

    # 收集箱任务不受共享影响：bob 看不到 admin 的收集箱任务
    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "admin收集箱任务"})
    task_id = r.json()["id"]
    r = await client.get(f"/api/v1/task/tasks/{task_id}", headers=bob_headers)
    assert r.status_code == 404
