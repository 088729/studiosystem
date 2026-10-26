from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_comment_image_upload(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch("app.services.storage.get_storage") as mock_get:
        mock_storage = mock_get.return_value
        mock_storage.upload = AsyncMock(return_value={
            "path": "task/comments/abc123.png",
            "url": "/uploads/task/comments/abc123.png",
            "size": 5,
        })

        # 上传图片：multipart → 存储后端 → 返回 url/path
        r = await client.post(
            "/api/v1/task/comments/upload-image",
            headers=headers,
            files={"file": ("pic.png", b"\x89PNG\x00", "image/png")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["url"].endswith("task/comments/abc123.png")
        assert body["path"] == "task/comments/abc123.png"
        # 透传到存储后端的目录（uuid 文件名防冲突）
        assert mock_storage.upload.await_args.args[2] == "task/comments"

        # 非图片类型 → 400
        r = await client.post(
            "/api/v1/task/comments/upload-image",
            headers=headers,
            files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
        )
        assert r.status_code == 400

        # 超过 5MB → 400
        r = await client.post(
            "/api/v1/task/comments/upload-image",
            headers=headers,
            files={"file": ("big.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")},
        )
        assert r.status_code == 400

    # 未登录 → 401
    r = await client.post(
        "/api/v1/task/comments/upload-image",
        files={"file": ("pic.png", b"\x89PNG\x00", "image/png")},
    )
    assert r.status_code == 401
