import asyncio
import json
import logging
from typing import Optional

from app.models.case.case_asset import CaseAsset
from app.models.case.case_version import CaseVersion
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


async def run_asset_gc(batch_size: int = 100) -> dict:
    """
    扫描 is_orphan=True 的资产，确认无版本引用后物理删除 SMB 文件和 DB 记录。
    """
    deleted = 0
    skipped = 0
    errors = 0

    orphan_assets = await CaseAsset.find(CaseAsset.is_orphan == True).limit(batch_size).to_list()
    if not orphan_assets:
        return {"deleted": 0, "skipped": 0, "errors": 0}

    # 收集所有版本的 root JSON 文本（仅处理 batch 内涉及的 map_id 可减少数据量）
    map_ids = list({asset.map_id for asset in orphan_assets})
    version_roots = []
    for map_id in map_ids:
        versions = await CaseVersion.find(CaseVersion.map_id == map_id).to_list()
        for version in versions:
            version_roots.append(json.dumps(version.root, ensure_ascii=False))

    all_roots_text = "\n".join(version_roots)
    storage = get_storage()

    for asset in orphan_assets:
        try:
            # 使用带引号的精确匹配，避免 a.png 误匹配 a.png2
            if f'"{asset.url}"' in all_roots_text:
                skipped += 1
                continue
            await storage.delete(asset.relative_path)
            await asset.delete()
            deleted += 1
        except Exception as exc:
            logger.exception("资产 GC 删除失败: asset_id=%s url=%s", asset.id, asset.url, exc_info=exc)
            errors += 1

    return {"deleted": deleted, "skipped": skipped, "errors": errors}


_gc_task: Optional[asyncio.Task] = None


async def _gc_loop(interval_seconds: int = 3600):
    """每小时执行一次资产 GC。"""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await run_asset_gc()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("资产 GC 循环异常，60s 后重试")
            await asyncio.sleep(60)


def start_asset_gc(interval_seconds: int = 3600):
    global _gc_task
    if _gc_task is None or _gc_task.done():
        _gc_task = asyncio.create_task(_gc_loop(interval_seconds))


def stop_asset_gc():
    global _gc_task
    if _gc_task and not _gc_task.done():
        _gc_task.cancel()
