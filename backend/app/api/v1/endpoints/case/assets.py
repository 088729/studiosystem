from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.api.deps import get_current_user, require_perm
from app.models.user import User
from app.schemas.case import AssetHashCheck, AssetOut
from app.services.case import asset_service

router = APIRouter()


def _asset_out(asset) -> AssetOut:
    return AssetOut(
        id=str(asset.id),
        map_id=asset.map_id,
        node_id=asset.node_id,
        url=asset.url,
        file_type=asset.file_type,
        file_size=asset.file_size,
        file_hash=asset.file_hash,
        relative_path=asset.relative_path,
        refer_count=asset.refer_count,
        created_at=asset.created_at,
    )


@router.post("/check_hash")
async def check_hash(
    data: AssetHashCheck,
    current_user: User = Depends(require_perm("xmind:edit")),
):
    asset = await asset_service.check_hash(data.map_id, data.file_hash)
    return {
        "exists": asset is not None,
        "asset": _asset_out(asset) if asset else None,
    }


@router.post("/upload")
async def upload_asset(
    map_id: str = Form(...),
    node_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("xmind:edit")),
):
    content = await file.read()
    asset = await asset_service.upload_asset(
        map_id=map_id,
        node_id=node_id,
        filename=file.filename or "upload",
        file_bytes=content,
    )
    return _asset_out(asset)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    current_user: User = Depends(require_perm("xmind:delete")),
):
    await asset_service.delete_asset(asset_id)
    return {"message": "已删除"}
