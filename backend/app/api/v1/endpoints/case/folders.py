from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_perm
from app.models.user import User
from app.schemas.case import FolderCreate, FolderMove, FolderOut, FolderRename, FolderTreeResponse
from app.services.case import folder_service

router = APIRouter()


def _folder_out(folder) -> FolderOut:
    return FolderOut(
        id=str(folder.id),
        name=folder.name,
        parent_id=folder.parent_id,
        depth=folder.depth,
        owner=folder.owner,
        created_at=folder.created_at,
    )


@router.get("/tree", response_model=FolderTreeResponse)
async def get_folder_tree(current_user: User = Depends(require_perm("xmind:view"))):
    folders = await folder_service.list_folders()
    return FolderTreeResponse(items=[_folder_out(f) for f in folders])


@router.post("", response_model=FolderOut)
async def create_folder(
    data: FolderCreate,
    current_user: User = Depends(require_perm("xmind:manage")),
):
    folder = await folder_service.create_folder(data.name, data.parent_id, current_user.username)
    return _folder_out(folder)


@router.patch("/{folder_id}", response_model=FolderOut)
async def rename_folder(
    folder_id: str,
    data: FolderRename,
    current_user: User = Depends(require_perm("xmind:manage")),
):
    folder = await folder_service.rename_folder(folder_id, data.name)
    return _folder_out(folder)


@router.patch("/{folder_id}/parent", response_model=FolderOut)
async def move_folder(
    folder_id: str,
    data: FolderMove,
    current_user: User = Depends(require_perm("xmind:manage")),
):
    folder = await folder_service.move_folder(folder_id, data.parent_id)
    return _folder_out(folder)


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(require_perm("xmind:manage")),
):
    await folder_service.delete_folder(folder_id)
    return {"message": "已删除"}
