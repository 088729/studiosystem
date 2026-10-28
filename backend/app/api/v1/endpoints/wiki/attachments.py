from fastapi import APIRouter, Depends, File, Response, UploadFile

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.wiki import AttachmentOut
from app.services.wiki import attachment_service
from app.services.wiki.vault_service import get_vault_or_404

router = APIRouter()


@router.post("", response_model=AttachmentOut)
async def upload_attachment(
    vault_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("wiki:edit")),
):
    """上传附件（multipart 字段名 file），保存到工作区 attachments/，随文档提交。"""
    vault = await get_vault_or_404(vault_id)
    data = await file.read()
    result = await attachment_service.save_attachment(vault, file.filename or "", data)
    return AttachmentOut(**result)


@router.get("/content")
async def attachment_content(
    vault_id: str,
    path: str,
    current_user: User = Depends(require_perm("wiki:view")),
):
    """读取附件字节（正文/预览里的图片、音视频均走这里）。"""
    vault = await get_vault_or_404(vault_id)
    data, media_type = await attachment_service.read_attachment(vault, path)
    return Response(content=data, media_type=media_type)
