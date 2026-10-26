import pytest


@pytest.mark.asyncio
async def test_folder_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/case/folders", headers=headers, json={"name": "TestFolder"})
    assert r.status_code == 200
    folder_id = r.json()["id"]

    r = await client.get("/api/v1/case/folders/tree", headers=headers)
    assert r.status_code == 200
    assert any(item["id"] == folder_id for item in r.json()["items"])

    r = await client.patch(f"/api/v1/case/folders/{folder_id}", headers=headers, json={"name": "RenamedFolder"})
    assert r.status_code == 200
    assert r.json()["name"] == "RenamedFolder"

    r = await client.delete(f"/api/v1/case/folders/{folder_id}", headers=headers)
    assert r.status_code == 200
