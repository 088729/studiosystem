"""索引同步：单篇 upsert / 全量重建。索引从 Git 工作区派生，可重建。"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.wiki.wiki_link import WikiLink
from app.models.wiki.wiki_page import WikiPage
from app.models.wiki.wiki_vault import WikiVault
from app.services.wiki import git_repo, link_parser
from app.services.wiki.vault_service import vault_dir

logger = logging.getLogger(__name__)


async def _path_set(vault_id: str) -> set:
    pages = await WikiPage.find(WikiPage.vault_id == vault_id).to_list()
    return {p.path for p in pages}


async def upsert_page_index(vault: WikiVault, path: str, content: str) -> WikiPage:
    """保存/新建/revert 后调用：解析并更新 wiki_pages 与 wiki_links。"""
    path_set = await _path_set(str(vault.id))
    path_set.add(path)
    parsed = link_parser.parse_doc(
        content,
        fallback_title=link_parser_fallback_title(path),
        src_path=path,
        path_set=path_set,
    )
    page = await WikiPage.find_one(
        WikiPage.vault_id == str(vault.id), WikiPage.path == path
    )
    now = datetime.now(timezone.utc)
    is_new_page = page is None
    if is_new_page:
        page = WikiPage(
            vault_id=str(vault.id),
            path=path,
            title=parsed.title,
            folder=folder_of(path),
            tags=parsed.tags,
            size=len(content.encode("utf-8")),
            body=parsed.body_text,
            created_at=now,
            updated_at=now,
        )
        await page.insert()
    else:
        page.title = parsed.title
        page.folder = folder_of(path)
        page.tags = parsed.tags
        page.size = len(content.encode("utf-8"))
        page.body = parsed.body_text
        page.updated_at = now
        await page.save()

    await WikiLink.find(
        WikiLink.vault_id == str(vault.id), WikiLink.src_path == path
    ).delete()
    for ref in parsed.links:
        await WikiLink(
            vault_id=str(vault.id),
            src_path=path,
            dst_path=ref.dst_path,
            dst_alias=ref.dst_alias,
            link_type=ref.link_type,
            is_resolved=ref.dst_path is not None,
        ).insert()

    # 新页面入库后，全库重解悬空链接（先建引用、后建目标的场景）
    if is_new_page:
        dangling = await WikiLink.find(
            WikiLink.vault_id == str(vault.id),
            WikiLink.is_resolved == False,  # noqa: E712
        ).to_list()
        path_set.add(path)
        for link in dangling:
            dst = link_parser.resolve_link(link.dst_alias, link.src_path, path_set)
            if dst:
                link.dst_path = dst
                link.is_resolved = True
                await link.save()
    return page


async def delete_page_index(vault_id: str, path: str) -> None:
    await WikiPage.find(WikiPage.vault_id == vault_id, WikiPage.path == path).delete()
    await WikiLink.find(WikiLink.vault_id == vault_id, WikiLink.src_path == path).delete()
    # 指向该文档的链接标记为未解析（悬空）
    dangling = await WikiLink.find(
        WikiLink.vault_id == vault_id, WikiLink.dst_path == path
    ).to_list()
    for link in dangling:
        link.is_resolved = False
        await link.save()


async def rebuild_index(vault: WikiVault) -> dict:
    """全量重建：清空两集合后遍历工作区 .md 文件重新解析。在线程中执行。"""
    vault_id = str(vault.id)
    await WikiLink.find(WikiLink.vault_id == vault_id).delete()
    await WikiPage.find(WikiPage.vault_id == vault_id).delete()

    root = vault_dir(vault)
    files = await asyncio.to_thread(git_repo.list_md_files, root)
    path_set = set(files)
    now = datetime.now(timezone.utc)

    pages: list = []
    links: list = []
    for path in files:
        try:
            content = await asyncio.to_thread(git_repo.read_file, root, path)
        except Exception:
            logger.exception("重建索引读取失败: vault=%s path=%s", vault_id, path)
            continue
        parsed = link_parser.parse_doc(
            content,
            fallback_title=link_parser_fallback_title(path),
            src_path=path,
            path_set=path_set,
        )
        pages.append(WikiPage(
            vault_id=vault_id,
            path=path,
            title=parsed.title,
            folder=folder_of(path),
            tags=parsed.tags,
            size=len(content.encode("utf-8")),
            body=parsed.body_text,
            created_at=now,
            updated_at=now,
        ))
        for ref in parsed.links:
            links.append(WikiLink(
                vault_id=vault_id,
                src_path=path,
                dst_path=ref.dst_path,
                dst_alias=ref.dst_alias,
                link_type=ref.link_type,
                is_resolved=ref.dst_path is not None,
            ))
    if pages:
        await WikiPage.insert_many(pages)
    if links:
        await WikiLink.insert_many(links)
    return {"pages": len(pages), "links": len(links)}


def link_parser_fallback_title(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name[: -len(".md")] if name.endswith(".md") else name


def folder_of(path: str) -> str:
    idx = path.rfind("/")
    return path[:idx] if idx > 0 else ""


# ---- 任务式重建（202 语义）：clone 后初始化 / 手动 rebuild 共用 ----

_rebuild_lock = asyncio.Lock()
_rebuild_tasks: dict = {}  # vault_id -> {"status": "running"|"done"|"error", "result": ..., "error": ...}


async def start_rebuild(vault: WikiVault) -> Optional[dict]:
    """已有任务在跑则返回其状态（前端据此轮询）；否则启动后台重建并返回 None。"""
    async with _rebuild_lock:
        info = _rebuild_tasks.get(str(vault.id))
        if info and info["status"] == "running":
            return info
        task = asyncio.create_task(_run_rebuild(vault))
        _rebuild_tasks[str(vault.id)] = {"status": "running", "task": task}
        return None


async def _run_rebuild(vault: WikiVault) -> None:
    info = _rebuild_tasks[str(vault.id)]
    try:
        result = await rebuild_index(vault)
        info["status"] = "done"
        info["result"] = result
    except Exception as e:
        logger.exception("重建索引失败: vault=%s", vault.id)
        info["status"] = "error"
        info["error"] = str(e)
    finally:
        info.pop("task", None)


def rebuild_status(vault_id: str) -> Optional[dict]:
    info = _rebuild_tasks.get(vault_id)
    if info is None:
        return None
    return {"status": info["status"], "result": info.get("result"), "error": info.get("error")}
