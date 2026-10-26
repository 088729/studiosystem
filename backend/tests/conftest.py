import os

# 测试隔离：测试一律使用独立测试库，避免向开发/正式库写入「共享清单」等测试数据
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/studio_system_test"
# 存储后端：测试一律走 local + 会话级临时目录。硬赋值而非 setdefault——
# pytest-dotenv 会把开发 .env 的值注入 os.environ，setdefault 会被它抢先污染
import tempfile
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="studio_test_storage_")

# 每次测试会话开始前清空测试库，保证用例间无跨轮残留（如通知偏好）影响结果
import pymongo

pymongo.MongoClient(os.environ["MONGODB_URI"]).drop_database("studio_system_test")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from contextlib import asynccontextmanager

from app.main import app
from app.db import init_database, close_motor_client
from app.services.permission import init_permissions
from app.services.init_data import init_admin_user


@asynccontextmanager
async def managed_lifespan():
    await init_database()
    await init_permissions()
    await init_admin_user()
    yield
    await close_motor_client()


@pytest_asyncio.fixture
async def client():
    async with managed_lifespan():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def admin_token(client):
    r = await client.post("/api/v1/common/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["access_token"]
