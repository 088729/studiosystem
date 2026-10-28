import pytest


@pytest.mark.asyncio
async def test_map_lifecycle(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post("/api/v1/case/maps", headers=headers, json={"title": "TestMap"})
    assert r.status_code == 200
    map_id = r.json()["id"]

    r = await client.get(f"/api/v1/case/maps/{map_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "TestMap"

    root_data = {
        "root": {
            "data": {"text": "TestMap", "uid": "root", "expand": True},
            "children": [
                {
                    "data": {"text": "Feature", "uid": "n1"},
                    "children": [
                        {"data": {"text": "Input", "uid": "n2"}, "children": [
                            {"data": {"text": "Result", "uid": "n3"}, "children": []}
                        ]}
                    ]
                }
            ]
        },
        "layout": "logicalStructure",
        "theme": {"template": "default", "config": {}},
        "view": {"transform": {"scale": 1, "x": 0, "y": 0}}
    }

    r = await client.post(f"/api/v1/case/maps/{map_id}/lock", headers=headers)
    assert r.status_code == 200

    r = await client.post(
        f"/api/v1/case/maps/{map_id}/snapshot",
        headers=headers,
        json={"root": root_data, "changelog": "test", "overwrite": False},
    )
    assert r.status_code == 200
    assert r.json()["version_no"] == 2

    r = await client.get(f"/api/v1/case/maps/{map_id}/versions", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r = await client.delete(f"/api/v1/case/maps/{map_id}/lock", headers=headers)
    assert r.status_code == 200
