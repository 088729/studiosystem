from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import CommentCreate, CommentOut
from app.services.task import comment_service

router = APIRouter()


def _comment_out(comment) -> CommentOut:
    return CommentOut(
        id=str(comment.id),
        task_id=comment.task_id,
        author=comment.author,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/tasks/{task_id}/comments")
async def list_comments(
    task_id: str,
    current_user: User = Depends(require_perm("task:view")),
):
    comments = await comment_service.list_comments(task_id, current_user.username)
    return {"items": [_comment_out(c) for c in comments]}


@router.post("/tasks/{task_id}/comments", response_model=CommentOut)
async def add_comment(
    task_id: str,
    data: CommentCreate,
    current_user: User = Depends(require_perm("task:view")),
):
    comment = await comment_service.add_comment(task_id, current_user.username, data.content)
    return _comment_out(comment)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def update_comment(
    comment_id: str,
    data: CommentCreate,
    current_user: User = Depends(require_perm("task:view")),
):
    comment = await comment_service.update_comment(comment_id, current_user.username, data.content)
    return _comment_out(comment)


@router.post("/comments/upload-image")
async def upload_comment_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("task:view")),
):
    """上传评论图片（转发 resourceplatform，返回 url 供评论 content 内嵌 markdown 图片）。"""
    file_bytes = await file.read()
    return await comment_service.upload_comment_image(
        file.filename or "image.png", file.content_type or "", file_bytes
    )


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(require_perm("task:view")),
):
    await comment_service.delete_comment(comment_id, current_user.username)
    return {"ok": True}
