from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import get_settings
from app.models.user import User, Role, SsoPlatformConfig
from app.models.case.case_folder import CaseFolder
from app.models.case.case_map import CaseMap
from app.models.case.case_version import CaseVersion
from app.models.case.case_asset import CaseAsset
from app.models.task.task import Task
from app.models.task.task_list import TaskList
from app.models.task.tag import Tag
from app.models.task.focus_session import FocusSession
from app.models.task.focus_preset import FocusPreset
from app.models.task.habit import Habit, HabitLog
from app.models.task.comment import TaskComment
from app.models.task.task_filter import TaskFilter
from app.models.task.task_settings import TaskSettings
from app.models.wiki.wiki_vault import WikiVault
from app.models.wiki.wiki_page import WikiPage
from app.models.wiki.wiki_link import WikiLink

_motor_client: AsyncIOMotorClient | None = None


async def get_motor_client() -> AsyncIOMotorClient:
    global _motor_client
    if _motor_client is None:
        settings = get_settings()
        # tz_aware=True：PyMongo 默认返回 naive UTC datetime，FastAPI 序列化后不带时区，
        # 前端 dayjs 会按浏览器本地时间解析导致整体偏移（东八区 +8h），此处统一返回 aware UTC。
        _motor_client = AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True)
    return _motor_client


async def close_motor_client() -> None:
    global _motor_client
    if _motor_client is not None:
        _motor_client.close()
        _motor_client = None


async def init_database() -> None:
    client = await get_motor_client()
    settings = get_settings()
    db = client.get_default_database()
    if db is None:
        raise RuntimeError("MONGODB_URI must include a database name")
    await init_beanie(
        database=db,
        document_models=[
            User,
            Role,
            SsoPlatformConfig,
            CaseFolder,
            CaseMap,
            CaseVersion,
            CaseAsset,
            TaskList,
            Tag,
            Task,
            FocusSession,
            FocusPreset,
            Habit,
            HabitLog,
            TaskComment,
            TaskFilter,
            TaskSettings,
            WikiVault,
            WikiPage,
            WikiLink,
        ],
    )
