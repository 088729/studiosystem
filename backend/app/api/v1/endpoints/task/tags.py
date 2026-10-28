from fastapi import APIRouter, Depends

from app.api.deps import require_perm
from app.models.user import User
from app.schemas.task import TagCreate, TagOut, TagUpdate
from app.services.task import tag_service

router = APIRouter()


def _tag_out(tag) -> TagOut:
    return TagOut(
        id=str(tag.id),
        name=tag.name,
        color=tag.color,
        parent_id=tag.parent_id,
        sort_order=tag.sort_order,
        created_at=tag.created_at,
    )


@router.get("")
async def list_tags(current_user: User = Depends(require_perm("task:view"))):
    items = await tag_service.list_tags(current_user.username)
    return {"items": [_tag_out(item) for item in items]}


@router.post("", response_model=TagOut)
async def create_tag(
    data: TagCreate,
    current_user: User = Depends(require_perm("task:create")),
):
    tag = await tag_service.create_tag(
        data.name, data.color, current_user.username, data.parent_id
    )
    return _tag_out(tag)


@router.patch("/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    current_user: User = Depends(require_perm("task:edit")),
):
    tag = await tag_service.update_tag(
        tag_id, data.model_dump(exclude_unset=True), current_user.username
    )
    return _tag_out(tag)


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(require_perm("task:delete")),
):
    await tag_service.delete_tag(tag_id, current_user.username)
    return {"ok": True}
