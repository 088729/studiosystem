from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.core.exceptions import conflict
from app.models.user import User
from app.schemas.wiki import BacklinkOut, GraphOut, SearchResult
from app.services.wiki import index_service, search_service
from app.services.wiki.vault_service import get_vault_or_404

router = APIRouter()


@router.get("/search", response_model=list[SearchResult])
async def search_pages(
    vault_id: str,
    q: str = "",
    tag: Optional[str] = None,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    return await search_service.search(vault, q, tag)


@router.get("/backlinks", response_model=list[BacklinkOut])
async def page_backlinks(
    vault_id: str,
    path: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    return await search_service.backlinks(vault, path)


@router.get("/graph", response_model=GraphOut)
async def graph_data(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    return await search_service.graph(vault)


@router.post("/rebuild-index")
async def rebuild_index(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    vault = await get_vault_or_404(vault_id)
    running = await index_service.start_rebuild(vault)
    if running:
        raise conflict("wiki_rebuild_running", "索引重建中，请稍后查询进度")
    return {"message": "重建任务已启动", "status": "running"}
