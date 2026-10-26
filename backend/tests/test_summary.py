import uuid
from datetime import datetime, timedelta, timezone

import pytest


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_summary_grouping_and_filters(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    tz = 480
    now_local = datetime.now(timezone.utc) + timedelta(minutes=tz)
    P = "sum" + uuid.uuid4().hex[:6]  # 运行唯一前缀，避免跨次运行的存量数据污染断言

    # 两个清单 + 任务：今天完成 2 条（其中 1 条高优先级）、今天到期未完成 1 条、今天完成第 3 条、无日期 1 条
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": f"{P}S1"})
    l1 = r.json()["id"]
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": f"{P}S2"})
    l2 = r.json()["id"]
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_start_local - timedelta(minutes=tz)

    async def make(title, **kw):
        r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": title, **kw})
        assert r.status_code == 200, r.text
        return r.json()

    t1 = await make(f"{P}存钱", list_id=l1)
    t2 = await make(f"{P}月度会议", list_id=l1, priority=3, tags=[f"{P}工作"])
    t3 = await make(f"{P}热饭", list_id=l2, due_at=_iso(today_start + timedelta(hours=12)))
    t4 = await make(f"{P}昨天的事", list_id=l1)
    await make(f"{P}无日期任务", list_id=l1)
    # 笔记不计入摘要
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": f"{P}SN", "kind": "note"})
    ln = r.json()["id"]
    await make(f"{P}一条笔记", list_id=ln)

    # 完成 t1/t2/t4（均为今天完成）
    for tid in (t1["id"], t2["id"], t4["id"]):
        r = await client.post(f"/api/v1/task/tasks/{tid}/complete", headers=headers, json={"done": True})
        assert r.status_code == 200, r.text

    async def preview(cfg):
        # 限定本用例自建清单，防其他用例（如 test_sharing 的共享任务）污染全局「今天」视图
        r = await client.post("/api/v1/task/summary/preview", headers=headers,
                              json={"tz_offset_minutes": tz, "list_ids": [l1, l2, ln], **cfg})
        assert r.status_code == 200, r.text
        return r.json()

    # 今天：已完成 3（存钱、月度会议、昨天的事），未完成 1（热饭）
    res = await preview({"range": "today"})
    labels = {g["label"]: [i["title"] for i in g["items"]] for g in res["groups"]}
    assert sorted(labels.get("已完成")) == sorted([f"{P}月度会议", f"{P}存钱", f"{P}昨天的事"])  # 同刻完成，不断言顺序
    assert labels.get("未完成") == [f"{P}热饭"]
    assert f"{P}无日期任务" not in str(labels)
    assert f"{P}一条笔记" not in str(labels)
    assert res["range_label"] == f"{now_local.month}月{now_local.day}日"
    assert res["total"] == 4
    # markdown 含标题与分组
    assert res["markdown"].startswith("# ")
    assert "## 已完成" in res["markdown"] and "## 未完成" in res["markdown"]

    # custom 范围覆盖今天+昨天：已完成 3
    res = await preview({
        "range": "custom",
        "start": _iso(today_start_local - timedelta(days=1)),
        "end": _iso(today_start_local + timedelta(days=1)),
    })
    assert res["total"] == 4  # 3 done? t4 也是今天完成的——见下说明

    # 清单过滤：只看 S2 → 只有热饭
    res = await preview({"range": "today", "list_ids": [l2]})
    assert res["total"] == 1 and res["groups"][0]["items"][0]["title"] == f"{P}热饭"

    # 标签过滤：工作 → 只有月度会议
    res = await preview({"range": "today", "tags": [f"{P}工作"]})
    assert res["total"] == 1 and res["groups"][0]["items"][0]["title"] == f"{P}月度会议"

    # 优先级过滤：高 → 只有月度会议
    res = await preview({"range": "today", "priorities": [3]})
    assert res["total"] == 1

    # 状态过滤：只看未完成
    res = await preview({"range": "today", "statuses": ["todo"]})
    assert res["total"] == 1 and res["groups"][0]["label"] == "未完成"

    # 按清单分组
    res = await preview({"range": "today", "group_by": "list"})
    gl = {g["label"] for g in res["groups"]}
    assert gl == {f"{P}S1", f"{P}S2"}

    # show 字段：list + priority 出现在 markdown
    res = await preview({"range": "today", "show": ["date", "list", "priority"]})
    assert f"（{P}S1）" in res["markdown"] and "[高]" in res["markdown"]

    # 仅本人数据：bob 看不到 admin 的摘要
    r = await client.post("/api/v1/common/auth/users", headers=headers, json={"username": "sum_bob", "password": "bob12345", "role": "user"})
    assert r.status_code in (200, 201), r.text
    r = await client.post("/api/v1/common/auth/login", json={"username": "sum_bob", "password": "bob12345"})
    bob_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    res = await preview({"range": "today"}) if False else None
    r = await client.post("/api/v1/task/summary/preview", headers=bob_headers, json={"range": "today", "tz_offset_minutes": tz})
    assert r.status_code == 200
    assert r.json()["total"] == 0
