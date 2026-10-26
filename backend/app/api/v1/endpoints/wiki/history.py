from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.wiki import DiffOut, HistoryEntry, RevertIn
from app.services.wiki import page_service
from app.services.wiki.vault_service import get_vault_or_404

router = APIRouter()


@router.get("", response_model=list[HistoryEntry])
async def page_history(
    vault_id: str,
    path: str,
    limit: int = 50,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    entries = await page_service.page_history(vault, path, limit)
    return [HistoryEntry(**e) for e in entries]


@router.get("/diff", response_model=DiffOut)
async def page_diff(
    vault_id: str,
    path: str,
    commit: str,
    compare: Optional[str] = None,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    result = await page_service.page_diff(vault, path, commit, compare)
    return DiffOut(**result)


@router.post("/revert")
async def revert_page(
    vault_id: str,
    data: RevertIn,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    return await page_service.revert_page(vault, data.path, data.commit, current_user.username)
