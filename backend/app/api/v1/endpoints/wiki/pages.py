from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_global_perms, require_perm
from app.models.user import User
from app.schemas.wiki import (
    CommitIn,
    CommitOut,
    LockIn,
    PageContentOut,
    PageCreate,
    PageMove,
    PageOut,
    PageSave,
    TreeNode,
)
from app.services.wiki import page_service
from app.services.wiki.vault_service import get_vault_or_404

router = APIRouter()


@router.get("/tree", response_model=list[TreeNode])
async def page_tree(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    return await page_service.list_tree(vault)


@router.get("/content", response_model=PageContentOut)
async def page_content(
    vault_id: str,
    path: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    data = await page_service.read_page(vault, path)
    return PageContentOut(**data)


@router.post("", response_model=PageOut)
async def create_page(
    vault_id: str,
    data: PageCreate,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    result = await page_service.create_page(vault, data.path, data.content, current_user.username)
    return PageOut(**result)


@router.put("/content", response_model=PageOut)
async def save_page(
    vault_id: str,
    data: PageSave,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    result = await page_service.save_page(
        vault, data.path, data.content, current_user.username, holder=data.holder
    )
    return PageOut(**result)


@router.delete("")
async def delete_page(
    vault_id: str,
    path: str,
    recursive: bool = False,
    current_user: User = Depends(require_perm("wiki:delete")),
):
    vault = await get_vault_or_404(vault_id)
    return await page_service.delete_page(vault, path, recursive, current_user.username)


@router.post("/move")
async def move_page(
    vault_id: str,
    data: PageMove,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    return await page_service.move_page(vault, data.src, data.dst, current_user.username)


@router.post("/commit", response_model=CommitOut)
async def commit_pages(
    vault_id: str,
    data: CommitIn,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    result = await page_service.commit_vault(vault, data.message, current_user.username)
    return CommitOut(**result)


@router.post("/lock")
async def acquire_lock(
    vault_id: str,
    data: LockIn,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    return await page_service.acquire_lock(
        str(vault.id), data.path, current_user.username, holder=data.holder
    )


@router.delete("/lock")
async def release_lock(
    vault_id: str,
    path: str,
    holder: Optional[str] = None,
    current_user: User = Depends(require_perm("wiki:edit")),
):
    vault = await get_vault_or_404(vault_id)
    perms = await get_global_perms(current_user)
    is_admin = "*" in perms
    await page_service.release_lock(
        str(vault.id), path, current_user.username, is_admin=is_admin, holder=holder
    )
    return {"message": "已释放"}
