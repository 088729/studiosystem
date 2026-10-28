from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.wiki import ImportDirIn, VaultCreate, VaultDetailOut, VaultOut, VaultUpdate
from app.services.wiki import vault_service
from app.services.wiki.vault_service import get_vault_or_404

router = APIRouter()


def _vault_out(vault) -> VaultOut:
    return VaultOut(
        id=str(vault.id),
        name=vault.name,
        description=vault.description,
        owner=vault.owner,
        remote_url=vault.remote_url,
        default_branch=vault.default_branch,
        auto_commit_interval=vault.auto_commit_interval,
        status=vault.status,
        status_message=vault.status_message,
        created_at=vault.created_at,
        updated_at=vault.updated_at,
    )


@router.get("")
async def list_vaults(current_user: User = Depends(require_perm("wiki:view"))):
    vaults = await vault_service.list_vaults()
    return {"items": [_vault_out(v) for v in vaults]}


@router.post("", response_model=VaultOut)
async def create_vault(
    data: VaultCreate,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    # 空库同步初始化；远程 clone 由服务层后台执行（status: cloning → indexing → ready），前端轮询
    vault = await vault_service.create_vault(
        name=data.name,
        owner=current_user.username,
        description=data.description,
        remote_url=data.remote_url,
        auto_commit_interval=data.auto_commit_interval,
    )
    return _vault_out(vault)


@router.post("/import-zip", response_model=VaultOut)
async def import_zip(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    auto_commit_interval: int = Form(300),
    current_user: User = Depends(require_perm("wiki:manage")),
):
    """上传 zip 压缩包导入为新文档库（后台解压建索引，前端轮询 status）。"""
    data = await file.read()
    vault = await vault_service.import_vault_zip(
        filename=file.filename or "import.zip",
        data=data,
        owner=current_user.username,
        name=name,
        auto_commit_interval=auto_commit_interval,
    )
    return _vault_out(vault)


@router.post("/import-dir", response_model=VaultOut)
async def import_dir(
    data: ImportDirIn,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    """导入服务器本地目录为新文档库（保留 .git 历史；后台建索引，前端轮询 status）。"""
    vault = await vault_service.import_vault_dir(
        src_path=data.path,
        owner=current_user.username,
        name=data.name,
    )
    return _vault_out(vault)


@router.get("/overview")
async def vaults_overview(current_user: User = Depends(require_perm("wiki:view"))):
    """列表页批量概览（文档数/未提交数/状态），一次请求替代 N 次详情请求。"""
    vaults = await vault_service.list_vaults()
    return {"items": await vault_service.vaults_overview(vaults)}


@router.get("/{vault_id}", response_model=VaultDetailOut)
async def get_vault(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    vault = await get_vault_or_404(vault_id)
    status = await vault_service.vault_status(vault)
    return VaultDetailOut(
        **_vault_out(vault).model_dump(),
        changes=status["changes"],
        doc_count=status["doc_count"],
        rebuild=status["rebuild"],
    )


@router.patch("/{vault_id}", response_model=VaultOut)
async def update_vault(
    vault_id: str,
    data: VaultUpdate,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    vault = await get_vault_or_404(vault_id)
    vault = await vault_service.update_vault(vault, **data.model_dump(exclude_none=True))
    return _vault_out(vault)


@router.delete("/{vault_id}")
async def delete_vault(
    vault_id: str,
    hard: bool = False,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    vault = await get_vault_or_404(vault_id)
    await vault_service.delete_vault(vault, hard=hard)
    vault_service.cleanup_vault_lock(vault_id)
    return {"message": "已删除"}


@router.post("/{vault_id}/pull")
async def pull_vault(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    vault = await get_vault_or_404(vault_id)
    return await vault_service.pull_vault(vault, current_user.username)


@router.post("/{vault_id}/push")
async def push_vault(
    vault_id: str,
    current_user: User = Depends(require_perm("wiki:manage")),
):
    vault = await get_vault_or_404(vault_id)
    return await vault_service.push_vault(vault, current_user.username)
