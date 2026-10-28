from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.db import init_database, close_motor_client
from app.api.v1.router import api_router
from app.services.permission import init_permissions
from app.services.init_data import init_admin_user
from app.services.case.asset_gc import start_asset_gc, stop_asset_gc
from app.services.task.reminder_loop import start_reminder_loop, stop_reminder_loop
from app.services.wiki.auto_commit import start_auto_commit, stop_auto_commit


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    await init_permissions()
    await init_admin_user()
    start_asset_gc()
    start_reminder_loop()
    start_auto_commit()
    yield
    stop_asset_gc()
    stop_reminder_loop()
    await stop_auto_commit()
    await close_motor_client()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# 本地文件存储：静态公开访问 /uploads/{...}（与原 ResourcePlatform 的公开 GET 语义一致）
if (settings.storage_backend or "local").lower() == "local":
    from pathlib import Path

    uploads_dir = Path(settings.storage_dir).resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
