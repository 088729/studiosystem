"""定时自动提交：每 Vault 按 auto_commit_interval 扫描，有变更则提交。"""
import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.wiki.wiki_vault import WikiVault
from app.services.wiki import git_repo
from app.services.wiki.vault_service import cleanup_vault_lock, email_suffix, vault_dir

logger = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task] = None
_last_run: dict = {}  # vault_id -> datetime
_last_gc: Optional[datetime] = None

# 软删库保留天数，超过后物理清理磁盘目录 + Mongo 记录
GC_RETENTION_DAYS = 30


async def _auto_commit_vault(vault: WikiVault) -> None:
    root = vault_dir(vault)
    if not root.exists():
        return
    try:
        hexsha = await asyncio.to_thread(
            git_repo.commit,
            root,
            "auto: snapshot",
            "wikibot",
            email_suffix(),
        )
        if hexsha:
            logger.info("wiki 自动提交: vault=%s commit=%s", vault.name, hexsha[:7])
    except Exception:
        logger.exception("wiki 自动提交失败: vault=%s", vault.name)


async def flush_all() -> None:
    """停机兜底：对所有有变更的 Vault 补一次提交。"""
    vaults = await WikiVault.find(WikiVault.is_deleted == False).to_list()  # noqa: E712
    for vault in vaults:
        try:
            if vault.status != "ready":
                continue
            root = vault_dir(vault)
            if root.exists() and await asyncio.to_thread(git_repo.has_changes, root):
                await _auto_commit_vault(vault)
        except Exception:
            logger.exception("wiki 停机 flush 失败: vault=%s", vault.name)


async def _gc_deleted_vaults(now: datetime) -> None:
    """软删库保留期过后物理清理（设计约定：30 天）。"""
    cutoff = now - timedelta(days=GC_RETENTION_DAYS)
    stale = await WikiVault.find(
        WikiVault.is_deleted == True,  # noqa: E712
        WikiVault.deleted_at != None,  # noqa: E711
        WikiVault.deleted_at < cutoff,
    ).to_list()
    for vault in stale:
        try:
            root = vault_dir(vault)
            if root.exists():
                await asyncio.to_thread(shutil.rmtree, root, True)
            await vault.delete()
            logger.info("wiki 软删库已物理清理: vault=%s", vault.name)
        except Exception:
            logger.exception("wiki 软删库清理失败: vault=%s", vault.name)


async def _loop(tick_seconds: int = 60):
    global _last_gc
    while True:
        try:
            await asyncio.sleep(tick_seconds)
            now = datetime.now(timezone.utc)
            # 每天一次：物理清理软删超过保留期的库
            if _last_gc is None or (now - _last_gc).total_seconds() >= 24 * 3600:
                _last_gc = now
                await _gc_deleted_vaults(now)
            vaults = await WikiVault.find(WikiVault.is_deleted == False).to_list()  # noqa: E712
            for vault in vaults:
                if vault.status != "ready":
                    continue  # 克隆/导入/索引构建中，不打扰
                interval = vault.auto_commit_interval or 0
                if interval <= 0:
                    continue
                last = _last_run.get(str(vault.id))
                if last and (now - last).total_seconds() < interval:
                    continue
                _last_run[str(vault.id)] = now
                await _auto_commit_vault(vault)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("wiki 自动提交循环异常，60s 后重试")
            await asyncio.sleep(60)


def start_auto_commit():
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_loop())


async def stop_auto_commit():
    """优雅停机：先 flush 所有 dirty Vault，再取消任务。"""
    global _loop_task
    if _loop_task and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
        _loop_task = None
    await flush_all()
    # 清理 per-vault 写锁，防泄漏
    for vault_id in list(_last_run):
        cleanup_vault_lock(vault_id)
    _last_run.clear()
