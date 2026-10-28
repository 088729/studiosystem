import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    r = await client.post("/api/v1/common/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fail(client):
    r = await client.post("/api/v1/common/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, admin_token):
    r = await client.get("/api/v1/common/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "admin"
