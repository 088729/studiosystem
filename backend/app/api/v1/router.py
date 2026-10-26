from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, roles, platform
from app.api.v1.endpoints.case import folders, maps, assets
from app.api.v1.endpoints.task import lists as task_lists, tags as task_tags, tasks as task_tasks, views as task_views
from app.api.v1.endpoints.task import focus as task_focus, focus_preset as task_focus_presets, habits as task_habits
from app.api.v1.endpoints.task import share as task_share, comments as task_comments
from app.api.v1.endpoints.task import filters as task_filters
from app.api.v1.endpoints.task import settings as task_settings
from app.api.v1.endpoints.task import summary as task_summary
from app.api.v1.endpoints.wiki import vaults as wiki_vaults, pages as wiki_pages
from app.api.v1.endpoints.wiki import history as wiki_history, explore as wiki_explore
from app.api.v1.endpoints.wiki import attachments as wiki_attachments

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/common/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/common/auth/users", tags=["用户管理"])
api_router.include_router(roles.router, prefix="/common/auth/roles", tags=["角色管理"])
api_router.include_router(platform.router, prefix="/common/platform", tags=["权限配置"])

api_router.include_router(folders.router, prefix="/case/folders", tags=["用例-文件夹"])
api_router.include_router(maps.router, prefix="/case/maps", tags=["用例-导图"])
api_router.include_router(assets.router, prefix="/case/assets", tags=["用例-资产"])

api_router.include_router(task_lists.router, prefix="/task/lists", tags=["任务-清单"])
api_router.include_router(task_tags.router, prefix="/task/tags", tags=["任务-标签"])
api_router.include_router(task_tasks.router, prefix="/task/tasks", tags=["任务"])
api_router.include_router(task_views.router, prefix="/task/views", tags=["任务-视图"])
api_router.include_router(task_focus.router, prefix="/task/focus", tags=["任务-番茄钟"])
api_router.include_router(task_focus_presets.router, prefix="/task/focus-presets", tags=["任务-常用专注"])
api_router.include_router(task_habits.router, prefix="/task/habits", tags=["任务-习惯打卡"])
api_router.include_router(task_share.router, prefix="/task/share", tags=["任务-共享"])
api_router.include_router(task_comments.router, prefix="/task", tags=["任务-评论"])
api_router.include_router(task_filters.router, prefix="/task/filters", tags=["任务-筛选器"])
api_router.include_router(task_settings.router, prefix="/task/settings", tags=["任务-设置"])
api_router.include_router(task_summary.router, prefix="/task", tags=["任务-摘要"])

api_router.include_router(wiki_vaults.router, prefix="/wiki/vaults", tags=["文档库"])
api_router.include_router(wiki_pages.router, prefix="/wiki/vaults/{vault_id}/pages", tags=["文档-页面"])
api_router.include_router(wiki_history.router, prefix="/wiki/vaults/{vault_id}/history", tags=["文档-历史"])
api_router.include_router(wiki_explore.router, prefix="/wiki/vaults/{vault_id}/explore", tags=["文档-探索"])
api_router.include_router(wiki_attachments.router, prefix="/wiki/vaults/{vault_id}/attachments", tags=["文档-附件"])
