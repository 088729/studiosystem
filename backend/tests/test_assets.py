from unittest.mock import patch, AsyncMock

import pytest


@pytest.mark.asyncio
async def test_asset_upload_and_delete(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/case/maps", headers=headers, json={"title": "AssetTest"})
    map_id = r.json()["id"]

    with patch("app.services.storage.get_storage") as mock_get_storage:
        mock_storage = mock_get_storage.return_value
        mock_storage.upload = AsyncMock(return_value={
            "url": f"/uploads/case/{map_id}/abc.png",
            "path": f"case/{map_id}/abc.png",
        })
        mock_storage.delete = AsyncMock(return_value={"deleted": f"case/{map_id}/abc.png"})

        # upload
        r = await client.post(
            "/api/v1/case/assets/upload",
            headers=headers,
            data={
                "map_id": map_id,
                "node_id": "n1",
            },
            files={"file": ("test.png", b"fake-image-content", "image/png")},
        )
        assert r.status_code == 200
        asset_id = r.json()["id"]
        file_hash = r.json()["file_hash"]

        # check hash
        r = await client.post(
            "/api/v1/case/assets/check_hash",
            headers=headers,
            json={"map_id": map_id, "file_hash": file_hash},
        )
        assert r.status_code == 200
        assert r.json()["exists"] is True

        # delete
        r = await client.delete(f"/api/v1/case/assets/{asset_id}", headers=headers)
        assert r.status_code == 200

        # check hash after delete
        r = await client.post(
            "/api/v1/case/assets/check_hash",
            headers=headers,
            json={"map_id": map_id, "file_hash": file_hash},
        )
        assert r.status_code == 200
        assert r.json()["exists"] is False
