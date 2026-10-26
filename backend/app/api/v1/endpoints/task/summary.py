from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import SummaryPreviewIn
from app.services.task import summary_service

router = APIRouter()


@router.post("/summary/preview")
async def preview_summary(
    data: SummaryPreviewIn,
    current_user: User = Depends(require_perm("task:view")),
):
    """按配置聚合任务摘要（对齐主流待办应用「摘要」智能清单），返回分组结构 + markdown 文本。"""
    return await summary_service.generate_summary(current_user.username, data.model_dump())
