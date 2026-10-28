from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks

from app.api.deps import get_current_user, require_perm
from app.core.exceptions import forbidden, bad_request
from app.models.user import User
from app.schemas.case import (
    MapCreate,
    MapCopy,
    MapDetailOut,
    MapDraftUpdate,
    MapMove,
    MapOut,
    MapRename,
    RollbackRequest,
    SnapshotRequest,
    VersionListResponse,
    VersionOut,
    VersionDetailOut,
)
from app.services.case import map_service, version_service
from app.services.case.xmind_import import import_xmind_file

router = APIRouter()


async def _map_out(map_obj, latest_versions: Optional[dict] = None) -> MapOut:
    latest_version = None
    if latest_versions is not None:
        latest_version = latest_versions.get(str(map_obj.id))
    last_modified = await map_service.get_last_modified(map_obj, latest_version)
    return MapOut(
        id=str(map_obj.id),
        title=map_obj.title,
        owner=map_obj.owner,
        folder_id=map_obj.folder_id,
        current_version=map_obj.current_version,
        created_at=map_obj.created_at,
        last_modified_at=last_modified,
    )


@router.get("")
async def list_maps(
    folder_id: Optional[str] = None,
    q: Optional[str] = None,
    list_all: Optional[bool] = False,
    current_user: User = Depends(require_perm("xmind:view")),
):
    maps = await map_service.list_maps(folder_id, q, list_all)

    # 批量查询最新版本，避免 N+1
    latest_versions = {}
    if maps:
        map_ids = [str(m.id) for m in maps]
        versions = await map_service.get_latest_versions_for_maps(map_ids)
        latest_versions = {v.map_id: v for v in versions}

    return {"items": [await _map_out(m, latest_versions) for m in maps]}


@router.post("", response_model=MapOut)
async def create_map(
    data: MapCreate,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    map_obj = await map_service.create_map(
        title=data.title,
        folder_id=data.folder_id,
        root=data.root,
        owner=current_user.username,
    )
    return await _map_out(map_obj)


@router.post("/import")
async def import_maps(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: User = Depends(require_perm("xmind:edit")),
):
    MAX_IMPORT_SIZE = 100 * 1024 * 1024  # 100MB
    results = []
    for file in files:
        try:
            content = await file.read()
            if len(content) > MAX_IMPORT_SIZE:
                raise bad_request(
                    "file_too_large",
                    f"导入文件大小超过限制 ({MAX_IMPORT_SIZE // 1024 // 1024}MB)",
                )
            map_obj = await import_xmind_file(
                content=content,
                filename=file.filename or "import.xmind",
                folder_id=folder_id,
                owner=current_user.username,
            )
            results.append({
                "map_id": str(map_obj.id),
                "title": map_obj.title,
                "version_no": map_obj.current_version,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
            })
    return {"results": results}


@router.get("/{map_id}", response_model=MapDetailOut)
async def get_map(
    map_id: str,
    current_user: User = Depends(require_perm("xmind:view")),
):
    detail = await map_service.get_map_detail(map_id)
    return MapDetailOut(**detail)


@router.patch("/{map_id}")
async def update_map(
    map_id: str,
    data: MapDraftUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    # 异步保存草稿
    background_tasks.add_task(
        map_service.update_map_draft,
        map_id,
        data.temp_content,
        data.title,
        current_user.username,
    )
    return {"message": "更新中"}


@router.delete("/{map_id}")
async def delete_map(
    map_id: str,
    current_user: User = Depends(require_perm("xmind:delete")),
):
    await map_service.delete_map(map_id)
    return {"message": "已删除"}


@router.patch("/{map_id}/folder")
async def move_map(
    map_id: str,
    data: MapMove,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    map_obj = await map_service.move_map(map_id, data.folder_id)
    return await _map_out(map_obj)


@router.post("/{map_id}/copy")
async def copy_map(
    map_id: str,
    data: MapCopy,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    map_obj = await map_service.copy_map(map_id, data.folder_id, current_user.username)
    return await _map_out(map_obj)


@router.post("/{map_id}/lock")
async def acquire_lock(
    map_id: str,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    await map_service.acquire_lock(map_id, current_user.username)
    return {"message": "锁定成功"}


@router.delete("/{map_id}/lock")
async def release_lock(
    map_id: str,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    from app.services.permission import compute_permissions, get_role_permissions_map

    role_permissions_map = await get_role_permissions_map()
    perms = compute_permissions(
        current_user.role_name,
        current_user.extra_permissions,
        current_user.denied_permissions,
        role_permissions_map,
    )
    is_admin = "*" in perms
    await map_service.release_lock(map_id, current_user.username, is_admin=is_admin)
    return {"message": "已释放"}


@router.get("/{map_id}/versions", response_model=VersionListResponse)
async def list_versions(
    map_id: str,
    offset: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_perm("xmind:view")),
):
    versions, total = await version_service.list_versions(map_id, offset, limit)
    return VersionListResponse(
        items=[
            VersionOut(
                id=str(v.id),
                map_id=v.map_id,
                version_no=v.version_no,
                changelog=v.changelog,
                operator_id=v.operator_id,
                created_at=v.created_at,
            )
            for v in versions
        ],
        total=total,
    )


@router.get("/{map_id}/versions/{version_no}", response_model=VersionDetailOut)
async def get_version(
    map_id: str,
    version_no: int,
    current_user: User = Depends(require_perm("xmind:view")),
):
    version = await version_service.get_version_or_404(map_id, version_no)
    return VersionDetailOut(
        id=str(version.id),
        map_id=version.map_id,
        version_no=version.version_no,
        changelog=version.changelog,
        operator_id=version.operator_id,
        created_at=version.created_at,
        root=version.root,
    )


@router.post("/{map_id}/snapshot")
async def create_snapshot(
    map_id: str,
    data: SnapshotRequest,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    version = await version_service.create_snapshot(
        map_id=map_id,
        root=data.root,
        changelog=data.changelog,
        overwrite=data.overwrite,
        operator=current_user.username,
    )
    return {
        "map_id": version.map_id,
        "version_no": version.version_no,
        "changelog": version.changelog,
    }


@router.post("/{map_id}/rollback")
async def rollback_version(
    map_id: str,
    data: RollbackRequest,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    version = await version_service.rollback_version(
        map_id=map_id,
        version_no=data.version_no,
        operator=current_user.username,
    )
    return {
        "map_id": version.map_id,
        "version_no": version.version_no,
        "changelog": version.changelog,
    }
