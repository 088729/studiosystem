"""文档读写、移动删除、编辑锁、提交。"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.core.exceptions import bad_request, conflict, not_found
from app.models.wiki.wiki_link import WikiLink
from app.models.wiki.wiki_page import WikiPage
from app.models.wiki.wiki_vault import WikiVault
from app.services.wiki import git_repo, index_service
from app.services.wiki.path_security import validate_rel_path
from app.services.wiki.vault_service import email_suffix, vault_dir, vault_write_lock

LOCK_TIMEOUT_MINUTES = 10
MAX_PAGE_BYTES = 1 * 1024 * 1024  # 单文档 >1MB 拒绝保存


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lock_expired(locked_at: Optional[datetime]) -> bool:
    if locked_at is None:
        return True
    return _now() - locked_at > timedelta(minutes=LOCK_TIMEOUT_MINUTES)


async def get_page_or_404(vault_id: str, path: str) -> WikiPage:
    page = await WikiPage.find_one(WikiPage.vault_id == vault_id, WikiPage.path == path)
    if page is None:
        raise not_found("wiki_page_not_found", f"文档不存在: {path}")
    return page


def _lock_token(operator: str, holder: Optional[str]) -> str:
    return holder or operator


def _locked_by_other(page: WikiPage, token: str) -> bool:
    """锁被他人（或其他窗口）持有且未过期。"""
    if not page.locked_by or _lock_expired(page.locked_at):
        return False
    return (page.lock_token or page.locked_by) != token


def _check_lock(page: WikiPage, operator: str, token: Optional[str] = None) -> None:
    """保存前校验编辑锁：他人/其他窗口持有且未过期 → 409。"""
    if _locked_by_other(page, _lock_token(operator, token)):
        raise conflict(
            "wiki_locked",
            f"{page.locked_by} 正在编辑该文档",
            {"lock_holder": page.locked_by},
        )


async def acquire_lock(
    vault_id: str, path: str, operator: str, holder: Optional[str] = None
) -> dict:
    page = await get_page_or_404(vault_id, path)
    if _locked_by_other(page, _lock_token(operator, holder)):
        raise conflict(
            "wiki_locked",
            f"{page.locked_by} 正在编辑该文档",
            {"lock_holder": page.locked_by},
        )
    page.locked_by = operator
    page.lock_token = _lock_token(operator, holder)
    page.locked_at = _now()
    await page.save()
    return {"lock_holder": page.locked_by, "locked_at": page.locked_at}


async def release_lock(
    vault_id: str,
    path: str,
    operator: str,
    is_admin: bool = False,
    holder: Optional[str] = None,
) -> None:
    page = await WikiPage.find_one(WikiPage.vault_id == vault_id, WikiPage.path == path)
    if page is None:
        return
    if page.locked_by and not is_admin:
        # 持锁令牌不匹配不释放（他人或其他窗口的锁）；旧数据无令牌时按用户名判定
        if (page.lock_token or page.locked_by) != _lock_token(operator, holder):
            return
    page.locked_by = None
    page.lock_token = None
    page.locked_at = None
    await page.save()


async def read_page(vault: WikiVault, path: str) -> dict:
    path = validate_rel_path(path)
    root = vault_dir(vault)
    file_path = root / path
    if not file_path.exists():
        raise not_found("wiki_page_not_found", f"文档不存在: {path}")
    content = await asyncio.to_thread(git_repo.read_file, root, path)
    page = await WikiPage.find_one(
        WikiPage.vault_id == str(vault.id), WikiPage.path == path
    )
    locked_by = None
    if page and page.locked_by and not _lock_expired(page.locked_at):
        locked_by = page.locked_by
    return {"path": path, "content": content, "locked_by": locked_by}


async def create_page(vault: WikiVault, path: str, content: str, operator: str) -> dict:
    path = validate_rel_path(path)
    if len(content.encode("utf-8")) > MAX_PAGE_BYTES:
        raise bad_request("wiki_page_too_large", "单文档超过 1MB，请拆分")
    async with vault_write_lock(str(vault.id)):
        root = vault_dir(vault)
        if (root / path).exists():
            raise conflict("wiki_page_exists", f"文档已存在: {path}")
        await asyncio.to_thread(git_repo.write_file, root, path, content)
        page = await index_service.upsert_page_index(vault, path, content)
    return {"path": page.path, "title": page.title}


async def save_page(
    vault: WikiVault, path: str, content: str, operator: str, holder: Optional[str] = None
) -> dict:
    path = validate_rel_path(path)
    if len(content.encode("utf-8")) > MAX_PAGE_BYTES:
        raise bad_request("wiki_page_too_large", "单文档超过 1MB，请拆分")
    async with vault_write_lock(str(vault.id)):
        page = await get_page_or_404(str(vault.id), path)
        _check_lock(page, operator, holder)
        # 无锁 → 保存并自动上锁（前端进入编辑即加锁，这里兜底）
        if not page.locked_by or (page.lock_token or page.locked_by) != _lock_token(operator, holder):
            page.locked_by = operator
            page.lock_token = _lock_token(operator, holder)
        page.locked_at = _now()
        root = vault_dir(vault)
        await asyncio.to_thread(git_repo.write_file, root, path, content)
        page = await index_service.upsert_page_index(vault, path, content)
        page.locked_by = operator
        page.lock_token = _lock_token(operator, holder)
        page.locked_at = _now()
        await page.save()
    return {"path": page.path, "title": page.title, "saved_at": page.updated_at}


async def delete_page(vault: WikiVault, path: str, recursive: bool, operator: str) -> dict:
    path = validate_rel_path(path, expect_md=False)
    async with vault_write_lock(str(vault.id)):
        root = vault_dir(vault)
        target = root / path
        if not target.exists():
            raise not_found("wiki_page_not_found", f"路径不存在: {path}")
        is_dir = target.is_dir()
        await asyncio.to_thread(git_repo.remove_path, root, path, recursive)
        vault_id = str(vault.id)
        if is_dir:
            # 目录：级联删除索引（含子路径）
            prefix = path + "/"
            await WikiPage.find(
                WikiPage.vault_id == vault_id,
                {"path": {"$regex": f"^{prefix}"}},
            ).delete()
            await WikiLink.find(
                WikiLink.vault_id == vault_id,
                {"src_path": {"$regex": f"^{prefix}"}},
            ).delete()
        await index_service.delete_page_index(vault_id, path)
    return {"message": "已删除", "path": path}


async def move_page(vault: WikiVault, src: str, dst: str, operator: str) -> dict:
    src = validate_rel_path(src, expect_md=False)
    dst = validate_rel_path(dst, expect_md=False)
    if src.endswith(".md") and not dst.endswith(".md"):
        raise bad_request("wiki_path_invalid", "移动 .md 文档的目标也必须以 .md 结尾")
    if src == dst:
        raise bad_request("wiki_path_invalid", "源路径与目标路径相同")
    async with vault_write_lock(str(vault.id)):
        root = vault_dir(vault)
        if not (root / src).exists():
            raise not_found("wiki_page_not_found", f"源路径不存在: {src}")
        if (root / dst).exists():
            raise conflict("wiki_page_exists", f"目标已存在: {dst}")
        await asyncio.to_thread(git_repo.move_file, root, src, dst)
        # 目录移动：级联更新索引路径
        vault_id = str(vault.id)
        if (root / dst).is_dir():
            prefix_src, prefix_dst = src + "/", dst + "/"
            pages = await WikiPage.find(
                WikiPage.vault_id == vault_id,
                {"path": {"$regex": f"^{prefix_src}"}},
            ).to_list()
            for p in pages:
                p.path = prefix_dst + p.path[len(prefix_src):]
                p.folder = index_service.folder_of(p.path)
                await p.save()
            links = await WikiLink.find(
                WikiLink.vault_id == vault_id,
                {"src_path": {"$regex": f"^{prefix_src}"}},
            ).to_list()
            for l in links:
                l.src_path = prefix_dst + l.src_path[len(prefix_src):]
                await l.save()
            return {"message": "已移动", "src": src, "dst": dst}
        # 单文档移动：迁移索引并重解析（链接的相对目标可能变化）
        page = await WikiPage.find_one(WikiPage.vault_id == vault_id, WikiPage.path == src)
        # 指向旧路径的链接改指新路径（保持 resolved）
        inbound = await WikiLink.find(
            WikiLink.vault_id == vault_id, WikiLink.dst_path == src
        ).to_list()
        for l in inbound:
            l.dst_path = dst
            await l.save()
        if page:
            content = await asyncio.to_thread(git_repo.read_file, root, dst)
            # 先落库改路径再重建索引：upsert 按 dst 查找记录，
            # 若 path 未先保存会以为「新页面」而为 dst 另建记录，旧记录残留在树上成幽灵节点
            page.path = dst
            page.folder = index_service.folder_of(dst)
            await page.save()
            await index_service.upsert_page_index(vault, dst, content)
    return {"message": "已移动", "src": src, "dst": dst}


async def commit_vault(vault: WikiVault, message: Optional[str], operator: str) -> dict:
    async with vault_write_lock(str(vault.id)):
        root = vault_dir(vault)
        msg = message or "update: snapshot"
        hexsha = await asyncio.to_thread(
            git_repo.commit, root, msg, operator, email_suffix()
        )
        if hexsha is None:
            return {"committed": False, "message": "没有需要提交的变更"}
        detail = await asyncio.to_thread(git_repo.commit_detail, root, hexsha)
        commit_date = detail["date"]
        for fpath in detail["files"]:
            page = await WikiPage.find_one(
                WikiPage.vault_id == str(vault.id), WikiPage.path == fpath
            )
            if page:
                page.last_commit_at = commit_date
                await page.save()
    return {
        "committed": True,
        "commit": hexsha,
        "message": msg,
        "files": detail["files"],
        "date": commit_date,
    }


async def page_history(vault: WikiVault, path: str, limit: int = 50) -> List[dict]:
    path = validate_rel_path(path)
    root = vault_dir(vault)
    return await asyncio.to_thread(git_repo.log_file, root, path, limit)


async def page_diff(vault: WikiVault, path: str, commit: str, compare: Optional[str]) -> dict:
    path = validate_rel_path(path)
    root = vault_dir(vault)
    text = await asyncio.to_thread(git_repo.diff_file, root, path, commit, compare)
    truncated = "已截断" in text.splitlines()[-1] if text else False
    return {"diff": text, "truncated": truncated}


async def revert_page(vault: WikiVault, path: str, commit: str, operator: str) -> dict:
    path = validate_rel_path(path)
    async with vault_write_lock(str(vault.id)):
        root = vault_dir(vault)
        hexsha = await asyncio.to_thread(
            git_repo.revert_file, root, path, commit, operator, email_suffix()
        )
        content = await asyncio.to_thread(git_repo.read_file, root, path)
        await index_service.upsert_page_index(vault, path, content)
    return {"commit": hexsha}


async def list_tree(vault: WikiVault) -> List[dict]:
    """由 wiki_pages 索引聚合目录树。"""
    pages = await WikiPage.find(WikiPage.vault_id == str(vault.id)).to_list()
    return _build_tree([{"path": p.path, "title": p.title, "folder": p.folder} for p in pages])


def _build_tree(page_rows: List[dict]) -> List[dict]:
    """folder 字段聚合 → 嵌套树（文件夹在前，按名称排序）。"""
    folders: dict = {}
    for row in page_rows:
        folder = row["folder"]
        parts = folder.split("/") if folder else []
        cursor = folders
        acc = ""
        for part in parts:
            acc = f"{acc}/{part}" if acc else part
            node = cursor.setdefault(part, {"__path": acc, "__children": {}, "__pages": []})
            cursor = node["__children"]
        cursor.setdefault("__pages", []).append(row)

    def to_list(level: dict) -> List[dict]:
        items = []
        for name in sorted(level.keys()):
            if name.startswith("__"):
                continue
            node = level[name]
            items.append({
                "type": "folder",
                "name": name,
                "path": node["__path"],
                "children": to_list(node["__children"]),
            })
        for row in sorted(level.get("__pages", []), key=lambda r: r["title"].lower()):
            items.append({
                "type": "page",
                "name": row["title"],
                "path": row["path"],
                "children": [],
            })
        return items

    return to_list(folders)
