import pytest


@pytest.mark.asyncio
async def test_version_rollback(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # create map
    r = await client.post("/api/v1/case/maps", headers=headers, json={"title": "VersionTest"})
    map_id = r.json()["id"]

    # lock
    await client.post(f"/api/v1/case/maps/{map_id}/lock", headers=headers)

    root_v1 = {
        "root": {
            "data": {"text": "VersionTest", "uid": "root", "expand": True},
            "children": [
                {
                    "data": {"text": "F1", "uid": "n1"},
                    "children": [
                        {"data": {"text": "I1", "uid": "n2"}, "children": [
                            {"data": {"text": "R1", "uid": "n3"}, "children": []}
                        ]}
                    ]
                }
            ]
        },
        "layout": "logicalStructure",
        "theme": {"template": "default", "config": {}},
        "view": {"transform": {"scale": 1, "x": 0, "y": 0}}
    }

    # snapshot v2
    r = await client.post(
        f"/api/v1/case/maps/{map_id}/snapshot",
        headers=headers,
        json={"root": root_v1, "changelog": "v2", "overwrite": False},
    )
    assert r.json()["version_no"] == 2

    # list versions
    r = await client.get(f"/api/v1/case/maps/{map_id}/versions", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    # get version 1
    r = await client.get(f"/api/v1/case/maps/{map_id}/versions/1", headers=headers)
    assert r.status_code == 200
    assert r.json()["version_no"] == 1

    # rollback to v1
    r = await client.post(
        f"/api/v1/case/maps/{map_id}/rollback",
        headers=headers,
        json={"version_no": 1},
    )
    assert r.status_code == 200
    assert r.json()["version_no"] == 3
    assert "回滚至 v1" in r.json()["changelog"]

    await client.delete(f"/api/v1/case/maps/{map_id}/lock", headers=headers)
