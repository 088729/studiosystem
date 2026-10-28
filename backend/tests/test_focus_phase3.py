"""第三期：专注统计聚合（趋势/小时/热力图/时间线/占比排行）+ 记录删除。"""
import pytest
from datetime import datetime, timedelta, timezone

FOCUS = "/api/v1/task/focus"
DETAIL = FOCUS + "/stats/detail"
TZ = 480  # 东八区，与测试数据构造保持一致


def iso_local(day_offset: int, hour: int, minute: int = 0) -> str:
    """构造本地时间对应的 UTC ISO（东八区）。"""
    now = datetime.now(timezone.utc) + timedelta(minutes=TZ)
    local = (now - timedelta(days=day_offset)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (local - timedelta(minutes=TZ)).isoformat()


@pytest.mark.asyncio
async def test_stats_detail_aggregations(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    today = datetime.now(timezone.utc) + timedelta(minutes=TZ)

    # 任务与清单
    r = await client.post("/api/v1/task/lists", headers=headers, json={"name": "e2e-统计清单"})
    list_id = r.json()["id"]
    task_ids = []
    for title in ("任务A", "任务B"):
        r = await client.post(
            "/api/v1/task/tasks",
            headers=headers,
            json={"title": title, "list_id": list_id},
        )
        task_ids.append(r.json()["id"])

    # 数据：今天 09 点 A 25m、今天 21 点 B 30m、昨天 09 点 A 45m、8 天前 15 点 A 60m
    records = [
        (0, 9, 25, task_ids[0]),
        (0, 21, 30, task_ids[1]),
        (1, 9, 45, task_ids[0]),
        (8, 15, 60, task_ids[0]),
        (8, 3, 15, None),  # 纯计时 3 点
    ]
    for d, h, m, tid in records:
        r = await client.post(
            FOCUS + "/records",
            headers=headers,
            json={
                "task_id": tid,
                "planned_minutes": m,
                "actual_seconds": m * 60,
                "started_at": iso_local(d, h),
            },
        )
        assert r.status_code == 200, r.text

    # 周界预期：今天/昨天/8 天前是否落在本周（周一为界）随运行日期变化，动态计算
    local_today = (datetime.now(timezone.utc) + timedelta(minutes=TZ)).date()
    monday = local_today - timedelta(days=local_today.weekday())
    in_week = [local_today - timedelta(days=d) >= monday for d, _, _, _ in records]
    week_total = sum(m for (_, _, m, _), ok_ in zip(records, in_week) if ok_)

    # 趋势（周）：总分钟=本周内记录之和
    r = await client.get(DETAIL, headers=headers, params={"kind": "trend", "period": "week", "tz_offset_minutes": TZ})
    t = r.json()
    assert t["range_label"] == "本周" and t["is_current"] is True
    assert len(t["labels"]) == 7 and len(t["minutes"]) == 7
    assert sum(t["minutes"]) == week_total
    assert t["avg_minutes"] == week_total // 7

    # 趋势（月）：含 8 天前那条（若跨月则不一定；总和 >= 100）
    r = await client.get(DETAIL, headers=headers, params={"kind": "trend", "period": "month", "tz_offset_minutes": TZ})
    assert sum(r.json()["minutes"]) >= 100

    # 小时分布（本月）：09 点=70m、21 点=30m
    r = await client.get(
        DETAIL,
        headers=headers,
        params={"kind": "hours", "month": f"{today.year}-{today.month:02d}", "tz_offset_minutes": TZ},
    )
    h = r.json()
    assert h["hours"][9] == 70 and h["hours"][21] == 30
    assert h["max_minutes"] == 70

    # 热力图（本年）：今天与 8 天前都有数据
    r = await client.get(DETAIL, headers=headers, params={"kind": "heatmap", "year": str(today.year), "tz_offset_minutes": TZ})
    days = r.json()["days"]
    assert len(days) >= 3

    # 时间线（本周）：7×24 矩阵，今天 09 点=25
    r = await client.get(DETAIL, headers=headers, params={"kind": "timeline", "tz_offset_minutes": TZ})
    tl = r.json()
    assert tl["week_label"] == "本周" and len(tl["cells"]) == 7 and len(tl["cells"][0]) == 24
    today_idx = (datetime.now(timezone.utc) + timedelta(minutes=TZ)).weekday()
    assert tl["cells"][today_idx][9] == 25

    # 占比（按任务·周）：任务A = 今天25 +（昨天45 若同周）；任务B = 30
    r = await client.get(DETAIL, headers=headers, params={"kind": "breakdown", "by": "task", "period": "week", "tz_offset_minutes": TZ})
    b = r.json()
    assert b["total_minutes"] == week_total
    names = {x["name"]: x["minutes"] for x in b["items"]}
    assert names.get("任务A") == (25 + (45 if in_week[2] else 0))
    assert names.get("任务B") == 30

    # 占比（按清单·周）：e2e-统计清单 = A+B
    r = await client.get(DETAIL, headers=headers, params={"kind": "breakdown", "by": "list", "period": "week", "tz_offset_minutes": TZ})
    bl = r.json()
    list_names = {x["name"]: x["minutes"] for x in bl["items"]}
    assert list_names.get("e2e-统计清单") == (25 + 30 + (45 if in_week[2] else 0))

    # 占比（按月·按任务）：今天(月初) 8 天前跨到上月 → 本月任务A=25+45（若 8 天前同月则 +60）
    r = await client.get(DETAIL, headers=headers, params={"kind": "breakdown", "by": "task", "period": "month", "tz_offset_minutes": TZ})
    bm = r.json()
    month_names = {x["name"]: x["minutes"] for x in bm["items"]}
    same_month_8d = (local_today - timedelta(days=8)).month == local_today.month
    assert month_names.get("任务A") == 25 + 45 + (60 if same_month_8d else 0)

    # 非法 kind → 400
    r = await client.get(DETAIL, headers=headers, params={"kind": "nope"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_focus_records_delete(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = []
    for _ in range(3):
        r = await client.post(
            FOCUS + "/records",
            headers=headers,
            json={"planned_minutes": 10, "actual_seconds": 600, "started_at": iso_local(0, 8)},
        )
        created.append(r.json()["id"])

    # running 不可删
    r = await client.post(FOCUS, headers=headers, json={"planned_minutes": 25})
    running_id = r.json()["id"]
    r = await client.request("DELETE", FOCUS + "/records", headers=headers, json={"ids": [running_id]})
    assert r.json()["deleted"] == 0
    await client.post(f"{FOCUS}/{running_id}/abandon", headers=headers)

    # 批量删 2 条
    r = await client.request("DELETE", FOCUS + "/records", headers=headers, json={"ids": created[:2]})
    assert r.json()["deleted"] == 2

    # 清空剩余
    r = await client.request("DELETE", FOCUS + "/records", headers=headers, json={"all": True})
    assert r.json()["deleted"] >= 1
