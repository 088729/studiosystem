import pytest


@pytest.mark.asyncio
async def test_task_settings_defaults_roundtrip(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 先重置为默认值（测试用真实库，e2e 可能留脏数据）
    await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={
            "default_list_id": None,
            "default_due": "none",
            "default_priority": 0,
            "default_reminder_minutes": None,
            "default_reminder_allday": "none",
            "default_range_minutes": 60,
            "default_tags": [],
            "daily_reminder_enabled": False,
            "daily_reminder_time": "09:00",
            "web_notification": False,
            "persistent_reminder_all": False,
            "reminder_sound": "default",
            "show_notification_detail": True,
            "completion_sound": "ding",
            "priority_sound_enabled": False,
            "priority_sound_high": "default",
            "priority_sound_medium": "default",
            "priority_sound_low": "default",
            "priority_sound_none": "default",
            "reminder_volume": 80,
            "show_lunar": False,
            "time_format": "24h",
            "week_start": "sunday",
            "show_week_number": False,
            "show_holiday": False,
            "show_timezone": False,
        },
    )

    # 首次读取：无记录时按默认值落库
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["default_list_id"] is None
    assert body["default_due"] == "none"
    assert body["default_priority"] == 0
    assert body["default_reminder_minutes"] is None
    assert body["default_reminder_allday"] == "none"
    assert body["default_range_minutes"] == 60
    assert body["default_tags"] == []
    assert body["daily_reminder_enabled"] is False
    assert body["daily_reminder_time"] == "09:00"
    assert body["web_notification"] is False
    assert body["persistent_reminder_all"] is False
    assert body["reminder_sound"] == "default"
    assert body["show_notification_detail"] is True
    assert body["completion_sound"] == "ding"
    assert body["priority_sound_enabled"] is False
    assert body["priority_sound_high"] == "default"
    assert body["priority_sound_medium"] == "default"
    assert body["priority_sound_low"] == "default"
    assert body["priority_sound_none"] == "default"
    assert body["reminder_volume"] == 80
    # 日期与时间（对齐主流待办应用）
    assert body["show_lunar"] is False
    assert body["time_format"] == "24h"
    assert body["week_start"] == "sunday"
    assert body["show_week_number"] is False
    assert body["show_holiday"] is False
    assert body["show_timezone"] is False

    # 整体 upsert
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={"default_due": "tomorrow", "default_priority": 2, "default_reminder_minutes": 30},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default_due"] == "tomorrow"
    assert body["default_priority"] == 2
    assert body["default_reminder_minutes"] == 30

    # 再读持久生效；未更新字段保持不变
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["default_due"] == "tomorrow"
    assert body["default_priority"] == 2
    assert body["default_reminder_minutes"] == 30
    assert body["default_list_id"] is None

    # 部分更新：只改优先级，其余不动
    r = await client.put("/api/v1/task/settings", headers=headers, json={"default_priority": 0})
    assert r.status_code == 200
    assert r.json()["default_due"] == "tomorrow"

    # 新增字段：默认时间段 / 全天提醒 / 默认标签 roundtrip
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={
            "default_range_minutes": 30,
            "default_reminder_allday": "same_day_9am",
            "default_tags": ["工作", "重要"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default_range_minutes"] == 30
    assert body["default_reminder_allday"] == "same_day_9am"
    assert body["default_tags"] == ["工作", "重要"]
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["default_tags"] == ["工作", "重要"]

    # 「结束时」（end 哨兵值）与自定义分钟数 roundtrip（对齐主流待办应用默认提醒选项）
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"default_reminder_minutes": "end"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["default_reminder_minutes"] == "end"
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["default_reminder_minutes"] == "end"
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"default_reminder_minutes": 45}
    )
    assert r.status_code == 200, r.text
    assert r.json()["default_reminder_minutes"] == 45
    # 非法值拒绝
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"default_reminder_minutes": "bogus"}
    )
    assert r.status_code == 422

    # 提醒与通知字段 roundtrip（每日提醒/网页提醒/全局持续提醒）
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={
            "daily_reminder_enabled": True,
            "daily_reminder_time": "08:30",
            "web_notification": True,
            "persistent_reminder_all": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["daily_reminder_enabled"] is True
    assert body["daily_reminder_time"] == "08:30"
    assert body["web_notification"] is True
    assert body["persistent_reminder_all"] is True
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["persistent_reminder_all"] is True

    # 提醒铃声 roundtrip（对齐主流待办应用提醒铃声选项）+ 非法值拒绝
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"reminder_sound": "beep"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["reminder_sound"] == "beep"
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["reminder_sound"] == "beep"
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"reminder_sound": "bogus"}
    )
    assert r.status_code == 422
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"reminder_sound": "default"}
    )
    assert r.status_code == 200

    # 显示通知详情 / 完成提示音 / 提醒音量 roundtrip + 音量越界拒绝
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={"show_notification_detail": False, "completion_sound": "waterdrop", "reminder_volume": 50},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["show_notification_detail"] is False
    assert body["completion_sound"] == "waterdrop"
    assert body["reminder_volume"] == 50
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["reminder_volume"] == 50
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"reminder_volume": 101}
    )
    assert r.status_code == 422
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"completion_sound": "bogus"}
    )
    assert r.status_code == 422
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={"show_notification_detail": True, "completion_sound": "ding", "reminder_volume": 80},
    )
    assert r.status_code == 200

    # 按优先级设置提醒 roundtrip + 非法值拒绝
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={"priority_sound_enabled": True, "priority_sound_high": "bell", "priority_sound_none": "crystal"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["priority_sound_enabled"] is True
    assert body["priority_sound_high"] == "bell"
    assert body["priority_sound_none"] == "crystal"
    r = await client.get("/api/v1/task/settings", headers=headers)
    assert r.json()["priority_sound_high"] == "bell"
    r = await client.put(
        "/api/v1/task/settings", headers=headers, json={"priority_sound_high": "bogus"}
    )
    assert r.status_code == 422
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={"priority_sound_enabled": False, "priority_sound_high": "default", "priority_sound_none": "default"},
    )
    assert r.status_code == 200

    # 恢复默认，避免污染其他用例/本地数据
    r = await client.put(
        "/api/v1/task/settings",
        headers=headers,
        json={
            "default_list_id": None,
            "default_due": "none",
            "default_priority": 0,
            "default_reminder_minutes": None,
            "default_reminder_allday": "none",
            "default_range_minutes": 60,
            "default_tags": [],
        },
    )
    assert r.status_code == 200
    assert r.json()["default_due"] == "none"
