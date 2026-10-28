import io
import zipfile

import pytest


@pytest.mark.asyncio
async def test_xmind_import(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    content_json = {
        "rootTopic": {
            "title": "导入测试",
            "children": {
                "attached": [
                    {"title": "功能1"}
                ]
            }
        }
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", __import__("json").dumps(content_json))

    r = await client.post(
        "/api/v1/case/maps/import",
        headers=headers,
        data={},
        files={"files": ("test.xmind", zip_buffer.getvalue(), "application/zip")},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["title"] == "导入测试"
    assert "map_id" in results[0]
