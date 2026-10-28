"""Vault 生命周期 + 仓库目录管理。"""
import asyncio
import logging
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import List, Optional

from bson import ObjectId

from app.core.config import get_settings
from app.core.exceptions import bad_request, conflict, not_found
from app.models.wiki.wiki_page import WikiPage
from app.models.wiki.wiki_vault import WikiVault
from app.services.wiki import git_repo

logger = logging.getLogger(__name__)

MAX_IMPORT_ZIP_SIZE = 200 * 1024 * 1024  # 导入 zip 上限 200MB

_repo_root: Optional[Path] = None


def repo_root() -> Path:
    """仓库根目录（WIKI_REPO_ROOT），惰性创建。"""
    global _repo_root
    if _repo_root is None:
        _repo_root = Path(get_settings().wiki_repo_root).resolve()
        _repo_root.mkdir(parents=True, exist_ok=True)
    return _repo_root


def vault_dir(vault: WikiVault) -> Path:
    """Vault 磁盘目录。repo_dir 由后端生成（uuid），杜绝路径注入。"""
    d = (repo_root() / vault.repo_dir).resolve()
    if not str(d).startswith(str(repo_root())):
        raise bad_request("wiki_path_invalid", "非法仓库目录")
    return d


def email_suffix() -> str:
    return get_settings().wiki_git_author_email_suffix


async def get_vault_or_404(vault_id: str) -> WikiVault:
    try:
        vault = await WikiVault.get(ObjectId(vault_id))
    except Exception:
        vault = None
    if vault is None or vault.is_deleted:
        raise not_found("wiki_vault_not_found", "文档库不存在")
    return vault


async def list_vaults() -> List[WikiVault]:
    return await WikiVault.find(WikiVault.is_deleted == False).to_list()  # noqa: E712


async def create_vault(
    name: str,
    owner: str,
    description: str = "",
    remote_url: Optional[str] = None,
    auto_commit_interval: int = 300,
) -> WikiVault:
    name = name.strip()
    if not name:
        raise bad_request("wiki_path_invalid", "库名不能为空")
    existing = await WikiVault.find_one(
        WikiVault.name == name, WikiVault.is_deleted == False  # noqa: E712
    )
    if existing:
        raise conflict("wiki_vault_exists", f"文档库已存在: {name}")

    vault = WikiVault(
        name=name,
        description=description,
        owner=owner,
        repo_dir=uuid.uuid4().hex,
        remote_url=remote_url,
        auto_commit_interval=auto_commit_interval,
        status="cloning" if remote_url else "indexing",
    )
    await vault.insert()
    if remote_url:
        # 大库克隆放后台任务，接口立即返回，前端轮询 status 直至 ready
        _spawn(_clone_and_index(vault, remote_url))
    else:
        await _init_and_index(vault)
    return vault


# ---- 后台任务：克隆 / 导入 + 索引，统一走状态机 ----

async def _set_status(vault: WikiVault, status: str, message: str = "") -> None:
    vault.status = status
    vault.status_message = message
    vault.updated_at = datetime.now(timezone.utc)
    await vault.save()


async def _init_and_index(vault: WikiVault) -> None:
    """空库 / 导入目录（无 .git）：init + 初始提交 + 建索引。"""
    root = vault_dir(vault)
    await asyncio.to_thread(git_repo.init_vault, root, "main", email_suffix())
    await asyncio.to_thread(
        git_repo.commit, root, "init: vault", vault.owner, email_suffix()
    )
    await _set_status(vault, "indexing")
    await _rebuild_and_ready(vault)


async def _rebuild_and_ready(vault: WikiVault) -> None:
    from app.services.wiki import index_service

    await index_service.rebuild_index(vault)
    await _set_status(vault, "ready")


async def _clone_and_index(vault: WikiVault, remote_url: str) -> None:
    root = vault_dir(vault)
    try:
        await asyncio.to_thread(git_repo.clone_vault, remote_url, root)
    except Exception as e:
        logger.exception("克隆远程仓库失败: vault=%s", vault.name)
        await _set_status(vault, "error", f"克隆失败: {e}")
        return
    await _set_status(vault, "indexing")
    try:
        await _rebuild_and_ready(vault)
    except Exception as e:
        logger.exception("克隆后建索引失败: vault=%s", vault.name)
        await _set_status(vault, "error", f"索引构建失败: {e}")


def _spawn(coro) -> None:
    """后台任务统一入口：异常必须被内部消化（状态机兜底），这里再补一道日志。"""
    def _log_result(t: asyncio.Task) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.exception("vault 后台任务未捕获异常: %s", exc)

    task = asyncio.create_task(coro)
    task.add_done_callback(_log_result)


# ---- 本地导入 ----

async def _check_name_available(name: str) -> None:
    existing = await WikiVault.find_one(
        WikiVault.name == name, WikiVault.is_deleted == False  # noqa: E712
    )
    if existing:
        raise conflict("wiki_vault_exists", f"文档库已存在: {name}")


def _new_vault_doc(name: str, owner: str, description: str, auto_commit_interval: int) -> WikiVault:
    return WikiVault(
        name=name,
        description=description,
        owner=owner,
        repo_dir=uuid.uuid4().hex,
        auto_commit_interval=auto_commit_interval,
        status="importing",
    )


def _safe_extract_zip(zip_path: Path, target: Path) -> None:
    """解压 zip 到 target，拒绝绝对路径与 .. 越界。在线程内执行。"""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in PurePosixPath(name).parts:
                raise bad_request("wiki_import_invalid", f"压缩包包含非法路径: {info.filename}")
        zf.extractall(target)


async def import_vault_zip(
    filename: str,
    data: bytes,
    owner: str,
    name: Optional[str] = None,
    auto_commit_interval: int = 300,
) -> WikiVault:
    """上传 zip 导入：解压进新 vault 目录，init + 初始提交 + 建索引。"""
    if len(data) > MAX_IMPORT_ZIP_SIZE:
        raise bad_request(
            "wiki_import_too_large",
            f"压缩包超过 {MAX_IMPORT_ZIP_SIZE // 1024 // 1024}MB 上限",
        )
    name = (name or Path(filename.replace("\\", "/")).stem or "导入的库").strip()
    await _check_name_available(name)
    vault = _new_vault_doc(name, owner, "", auto_commit_interval)
    root = vault_dir(vault)
    tmp_zip = repo_root() / f".import-{vault.repo_dir}.zip"
    try:
        await asyncio.to_thread(tmp_zip.write_bytes, data)
        root.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(_safe_extract_zip, tmp_zip, root)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    finally:
        tmp_zip.unlink(missing_ok=True)
    await vault.insert()
    _spawn(_import_finalize(vault, f"import: {filename}"))
    return vault


async def import_vault_dir(
    src_path: str,
    owner: str,
    name: Optional[str] = None,
    auto_commit_interval: int = 300,
) -> WikiVault:
    """导入服务器本地目录：有 .git 则 local clone（保留历史），否则复制 + init。"""
    src = Path(src_path).resolve()
    if not src.is_dir():
        raise not_found("wiki_import_source_missing", f"目录不存在: {src_path}")
    name = (name or src.name).strip()
    await _check_name_available(name)
    vault = _new_vault_doc(name, owner, "", auto_commit_interval)
    await vault.insert()
    root = vault_dir(vault)

    async def _do_import() -> None:
        try:
            if (src / ".git").exists():
                await asyncio.to_thread(git_repo.clone_vault, str(src), root)
                await _set_status(vault, "indexing")
            else:
                await asyncio.to_thread(shutil.copytree, src, root)
                await asyncio.to_thread(
                    git_repo.init_vault, root, "main", email_suffix(), True
                )
                await asyncio.to_thread(
                    git_repo.commit, root, f"import: {src.name}", owner, email_suffix()
                )
                await _set_status(vault, "indexing")
            await _rebuild_and_ready(vault)
        except Exception as e:
            logger.exception("导入目录失败: vault=%s src=%s", vault.name, src)
            await _set_status(vault, "error", f"导入失败: {e}")

    _spawn(_do_import())
    return vault


async def _import_finalize(vault: WikiVault, message: str) -> None:
    """zip 导入落盘后的统一收尾：init 仓库 + 初始提交 + 建索引。"""
    try:
        root = vault_dir(vault)
        await asyncio.to_thread(git_repo.init_vault, root, "main", email_suffix(), True)
        await asyncio.to_thread(
            git_repo.commit, root, message, vault.owner, email_suffix()
        )
        await _set_status(vault, "indexing")
        await _rebuild_and_ready(vault)
    except Exception as e:
        logger.exception("zip 导入收尾失败: vault=%s", vault.name)
        await _set_status(vault, "error", f"导入失败: {e}")


async def update_vault(vault: WikiVault, **fields) -> WikiVault:
    allowed = {"name", "description", "remote_url", "auto_commit_interval", "visibility"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            if key == "name" and value != vault.name:
                value = str(value).strip()
                if not value:
                    raise bad_request("wiki_path_invalid", "库名不能为空")
                dup = await WikiVault.find_one(
                    WikiVault.name == value, WikiVault.is_deleted == False  # noqa: E712
                )
                if dup and str(dup.id) != str(vault.id):
                    raise conflict("wiki_vault_exists", f"文档库已存在: {value}")
            setattr(vault, key, value)
    vault.updated_at = datetime.now(timezone.utc)
    await vault.save()
    return vault


async def delete_vault(vault: WikiVault, hard: bool = False) -> None:
    if hard:
        await asyncio.to_thread(shutil.rmtree, vault_dir(vault), True)
        await vault.delete()
    else:
        vault.is_deleted = True
        vault.deleted_at = datetime.now(timezone.utc)
        await vault.save()


async def vault_status(vault: WikiVault) -> dict:
    """详情 + 未提交变更列表 + 重建索引任务状态。"""
    from app.services.wiki import index_service

    root = vault_dir(vault)
    changes = []
    if root.exists():
        try:
            changes = await asyncio.to_thread(git_repo.status, root)
        except Exception:
            changes = []  # 克隆/导入进行中，尚未成为合法 git 仓库
    doc_count = await WikiPage.find(WikiPage.vault_id == str(vault.id)).count()
    return {
        "changes": changes,
        "doc_count": doc_count,
        "rebuild": index_service.rebuild_status(str(vault.id)),
    }


async def vaults_overview(vaults: List[WikiVault]) -> List[dict]:
    """列表页批量概览：一次聚合拿全部库的文档数，git status 并发执行。

    替代前端 per-vault 详情请求（N+1）：HTTP 往返从 N 次降为 1 次，
    文档数从 N 次 count 降为 1 次 aggregation。
    """
    counts: dict = {}
    coll = WikiPage.get_motor_collection()
    async for row in coll.aggregate([{"$group": {"_id": "$vault_id", "n": {"$sum": 1}}}]):
        counts[str(row["_id"])] = row["n"]

    async def one(vault: WikiVault) -> dict:
        change_count = 0
        root = vault_dir(vault)
        if root.exists() and vault.status == "ready":
            try:
                change_count = len(await asyncio.to_thread(git_repo.status, root))
            except Exception:
                change_count = 0  # 非法 git 仓库等场景按 0 处理
        return {
            "id": str(vault.id),
            "doc_count": counts.get(str(vault.id), 0),
            "change_count": change_count,
            "status": vault.status,
            "status_message": vault.status_message,
        }

    return list(await asyncio.gather(*[one(v) for v in vaults]))


async def pull_vault(vault: WikiVault, operator: str) -> dict:
    root = vault_dir(vault)
    if not root.exists():
        raise not_found("wiki_vault_not_found", "仓库目录不存在")
    try:
        await asyncio.to_thread(git_repo.pull, root, operator, email_suffix())
    except git_repo.WikiGitError as e:
        raise conflict("wiki_pull_conflict", str(e), {"files": e.conflict_files})
    except Exception as e:
        from app.core.exceptions import bad_gateway
        raise bad_gateway(f"远程同步失败: {e}")
    # pull 后增量重建索引
    from app.services.wiki import index_service
    result = await index_service.rebuild_index(vault)
    return {"message": "pull 完成", "rebuild": result}


async def push_vault(vault: WikiVault, operator: str) -> dict:
    root = vault_dir(vault)
    if not root.exists():
        raise not_found("wiki_vault_not_found", "仓库目录不存在")
    try:
        await asyncio.to_thread(git_repo.push, root, operator, email_suffix())
    except git_repo.WikiGitError as e:
        raise conflict("wiki_push_rejected", str(e))
    except Exception as e:
        from app.core.exceptions import bad_gateway
        raise bad_gateway(f"远程同步失败: {e}")
    return {"message": "push 完成"}


# ---- per-vault 写操作串行化（asyncio 锁，惰性创建；Vault 删除时清理） ----

_vault_locks: dict = {}


def vault_write_lock(vault_id: str) -> asyncio.Lock:
    lock = _vault_locks.get(vault_id)
    if lock is None:
        lock = asyncio.Lock()
        _vault_locks[vault_id] = lock
    return lock


def cleanup_vault_lock(vault_id: str) -> None:
    _vault_locks.pop(vault_id, None)
