import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId

from app.core.exceptions import not_found, bad_request
from app.models.case.case_asset import CaseAsset
from app.services.case.map_service import get_map_or_404, is_valid_oid


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _ext_from_filename(filename: str) -> str:
    ext = Path(filename).suffix
    return ext if ext else ".bin"


def _ext_to_mime(ext: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return mapping.get(ext.lower(), "application/octet-stream")


async def get_asset_or_404(asset_id: str) -> CaseAsset:
    if not is_valid_oid(asset_id):
        raise not_found("asset_not_found", "资产不存在")
    asset = await CaseAsset.get(ObjectId(asset_id))
    if asset is None:
        raise not_found("asset_not_found", "资产不存在")
    return asset


async def check_hash(map_id: str, file_hash: str) -> Optional[CaseAsset]:
    asset = await CaseAsset.find_one(
        CaseAsset.map_id == map_id,
        CaseAsset.file_hash == file_hash,
        CaseAsset.is_orphan == False,
    )
    return asset


async def upload_asset(
    map_id: str,
    node_id: str,
    filename: str,
    file_bytes: bytes,
) -> CaseAsset:
    await get_map_or_404(map_id)

    file_hash = _md5(file_bytes)
    ext = _ext_from_filename(filename)

    existing = await check_hash(map_id, file_hash)
    if existing is not None:
        existing.refer_count += 1
        await existing.save()
        return existing

    relative_path = f"case/{map_id}/{file_hash}{ext}"
    from app.services.storage import get_storage

    result = await get_storage().upload(
        file_bytes=file_bytes,
        filename=f"{file_hash}{ext}",
        path=f"case/{map_id}",
    )

    url = result.get("url") or f"/uploads/{relative_path}"
    asset = CaseAsset(
        map_id=map_id,
        node_id=node_id,
        url=url,
        file_type=_ext_to_mime(ext),
        file_size=len(file_bytes),
        file_hash=file_hash,
        relative_path=relative_path,
        refer_count=1,
    )
    await asset.insert()
    return asset


async def delete_asset(asset_id: str) -> None:
    """删除资产引用。引用归零时标记为 orphan，由 GC 异步物理删除。"""
    asset = await get_asset_or_404(asset_id)
    asset.refer_count -= 1
    if asset.refer_count <= 0:
        asset.is_orphan = True
    await asset.save()
