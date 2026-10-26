from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_task_attachment_upload_and_remove(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/task/tasks", headers=headers, json={"title": "附件测试"})
    task_id = r.json()["id"]

    with patch("app.services.storage.get_storage") as mock_get:
        mock_storage = mock_get.return_value
        mock_storage.upload = AsyncMock(return_value={
            "path": f"task/{task_id}/note.png",
            "url": f"/uploads/task/{task_id}/note.png",
            "size": 12,
        })

        # 上传：multipart → 存储后端 → 登记引用（附件仅允许图片类型）
        r = await client.post(
            f"/api/v1/task/tasks/{task_id}/attachments/upload",
            headers=headers,
            files={"file": ("note.png", b"hello attach", "image/png")},
        )
        assert r.status_code == 200, r.text
        atts = r.json()["attachments"]
        assert len(atts) == 1
        assert atts[0]["name"] == "note.png"
        assert atts[0]["resource_id"] == f"task/{task_id}/note.png"
        assert atts[0]["url"].endswith(f"task/{task_id}/note.png")
        assert atts[0]["size"] == 12
        # 透传给存储后端的目录
        assert mock_storage.upload.await_args.args[2] == f"task/{task_id}"

        # 非图片类型 → 400
        r = await client.post(
            f"/api/v1/task/tasks/{task_id}/attachments/upload",
            headers=headers,
            files={"file": ("note.txt", b"hello attach", "text/plain")},
        )
        assert r.status_code == 400

    # 详情返回附件
    r = await client.get(f"/api/v1/task/tasks/{task_id}", headers=headers)
    assert len(r.json()["attachments"]) == 1

    # 移除引用
    r = await client.delete(
        f"/api/v1/task/tasks/{task_id}/attachments/task/{task_id}/note.png", headers=headers
    )
    assert r.status_code == 200
    r = await client.get(f"/api/v1/task/tasks/{task_id}", headers=headers)
    assert r.json()["attachments"] == []

    # 不存在任务的附件上传 → 404
    with patch("app.services.storage.get_storage") as mock_get:
        mock_get.return_value.upload = AsyncMock()
        r = await client.post(
            "/api/v1/task/tasks/000000000000000000000000/attachments/upload",
            headers=headers,
            files={"file": ("a.png", b"x", "image/png")},
        )
        assert r.status_code == 404

    await client.delete(f"/api/v1/task/tasks/{task_id}", headers=headers)
