"""任务评论服务。可见性跟随任务可见性。"""
import uuid
from pathlib import Path
from typing import List

from bson import ObjectId

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.task.comment import TaskComment
from app.models.task.task_list import TaskList
from app.services.case.folder_service import is_valid_oid
from app.services.task.task_service import get_task_or_404

# 评论图片：类型/大小约束（文件本体转发 resourceplatform，content 内嵌 markdown 图片）
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


async def upload_comment_image(filename: str, content_type: str, file_bytes: bytes) -> dict:
    """上传评论图片（task/comments/ 目录），返回 {"url", "path"}。存储后端由 STORAGE_BACKEND 决定。"""
    from app.services.storage import get_storage

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise bad_request("invalid_image_type", "仅支持 png/jpg/gif/webp/bmp 图片")
    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise bad_request("image_too_large", "图片大小不能超过 5MB")
    ext = Path(filename).suffix.lower() or ".png"
    # path 是目录语义（最终为 {path}/{filename}），用 uuid 文件名防冲突
    resp = await get_storage().upload(file_bytes, f"{uuid.uuid4().hex}{ext}", "task/comments")
    return {"url": resp.get("url"), "path": resp.get("path")}


async def list_comments(task_id: str, user: str) -> List[TaskComment]:
    await get_task_or_404(task_id, user)  # 校验可见
    return await TaskComment.find(TaskComment.task_id == task_id).sort("created_at").to_list()


async def add_comment(task_id: str, user: str, content: str) -> TaskComment:
    await get_task_or_404(task_id, user)
    comment = TaskComment(task_id=task_id, author=user, content=content)
    await comment.insert()
    return comment


async def update_comment(comment_id: str, user: str, content: str) -> TaskComment:
    """仅评论作者本人可编辑。"""
    if not is_valid_oid(comment_id):
        raise not_found("comment_not_found", "评论不存在")
    comment = await TaskComment.get(ObjectId(comment_id))
    if comment is None:
        raise not_found("comment_not_found", "评论不存在")
    if comment.author != user:
        raise forbidden("仅评论作者可编辑")
    comment.content = content
    await comment.save()
    return comment


async def delete_comment(comment_id: str, user: str) -> None:
    """评论作者本人，或该任务所属清单的 owner 可删。"""
    if not is_valid_oid(comment_id):
        raise not_found("comment_not_found", "评论不存在")
    comment = await TaskComment.get(ObjectId(comment_id))
    if comment is None:
        raise not_found("comment_not_found", "评论不存在")
    if comment.author == user:
        await comment.delete()
        return
    # 清单 owner 可删
    task = await get_task_or_404(comment.task_id, user)
    if task.list_id and is_valid_oid(task.list_id):
        task_list = await TaskList.get(ObjectId(task.list_id))
        if task_list is not None and task_list.owner == user:
            await comment.delete()
            return
    raise forbidden("仅评论作者或清单所有者可删除")
