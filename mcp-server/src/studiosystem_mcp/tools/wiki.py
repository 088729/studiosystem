"""Wiki-domain tools: read (P0) + write/history (P2).

Module-level helpers (`get_page` / `write_page` / `unified_diff`) are shared
with the workflow domain (P2), which generates pages then reuses the exact
same lock → PUT → commit → release flow.
"""

from __future__ import annotations

import difflib
import logging

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import wiki as wiki_ad
from ..context import AppContext
from ..errors import StudioError
from ..policy.flow import confirm_gate

logger = logging.getLogger(__name__)

LOCK_HOLDER = "mcp-bot@mcp"


async def get_page(ctx: AppContext, vault_id: str, path: str) -> dict | None:
    """GET page content; None when the page does not exist (404)."""
    try:
        return await ctx.client.get(
            f"/wiki/vaults/{vault_id}/pages/content", params={"path": path}
        )
    except StudioError as exc:
        if exc.status == 404:
            return None
        raise


def unified_diff(old: str, new: str, path: str, *, max_chars: int = 20000) -> str:
    """Compact unified diff for confirmation previews."""
    diff = "\n".join(
        difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile=f"a/{path}",
                             tofile=f"b/{path}", lineterm="", n=3)
    )
    if len(diff) > max_chars:
        return diff[:max_chars] + "\n…（diff 过长已截断）"
    return diff


async def write_page(
    ctx: AppContext,
    vault_id: str,
    path: str,
    content: str,
    *,
    commit: bool = True,
    message: str | None = None,
    holder: str = LOCK_HOLDER,
) -> dict:
    """lock → PUT full content → optional commit → always release (finally)."""
    await ctx.client.post(
        f"/wiki/vaults/{vault_id}/pages/lock", json={"path": path, "holder": holder}
    )
    try:
        page = await ctx.client.put(
            f"/wiki/vaults/{vault_id}/pages/content",
            json={"path": path, "content": content, "holder": holder},
        )
        result: dict = {"ok": True, "path": page.get("path", path), "committed": False}
        if commit:
            commit_out = await ctx.client.post(
                f"/wiki/vaults/{vault_id}/pages/commit",
                json={"message": message} if message else {},
            )
            result["commit"] = commit_out
            result["committed"] = bool((commit_out or {}).get("committed"))
        return result
    finally:
        try:
            await ctx.client.delete(
                f"/wiki/vaults/{vault_id}/pages/lock", params={"path": path, "holder": holder}
            )
        except Exception as exc:  # release failure must not mask the write result
            logger.warning("wiki lock release failed for %s: %s", path, exc)


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="wiki_list_vaults",
        description=(
            "列出 Wiki 文档库及状态（ready/cloning/indexing/importing/error）。"
            "非 ready 的库请稍后重试；后续 wiki_* 工具都需要 vault_id。"
        ),
    )
    async def wiki_list_vaults() -> dict:
        try:
            data = await ctx.client.get("/wiki/vaults")
            items = [
                {**v, "status_label": wiki_ad.status_label(v.get("status"))} for v in data.get("items", [])
            ]
            return {"ok": True, "count": len(items), "vaults": items}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="wiki_tree",
        description="文档库目录树（文本形式，含每页的完整路径）。",
    )
    async def wiki_tree(vault_id: str) -> dict:
        try:
            nodes = await ctx.client.get(f"/wiki/vaults/{vault_id}/pages/tree")
            return {"ok": True, "vault_id": vault_id, "tree": wiki_ad.render_tree(nodes or [])}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="wiki_read_page",
        description=(
            "读取一页 Markdown 正文。path 必须是库内 .md 相对路径（如 docs/a.md）。"
            "超长内容自动截断（标记省略位置）。"
        ),
    )
    async def wiki_read_page(vault_id: str, path: str) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            data = await ctx.client.get(
                f"/wiki/vaults/{vault_id}/pages/content", params={"path": rel}
            )
            content, truncated = wiki_ad.trim_page_content(data.get("content") or "")
            return {
                "ok": True,
                "vault_id": vault_id,
                "path": data.get("path", rel),
                "title": wiki_ad.page_title_from_path(rel),
                "locked_by": data.get("locked_by"),
                "content": content,
                "truncated": truncated,
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="wiki_search",
        description=(
            "Wiki 检索：mode=search 全文检索（q 关键词）/ backlinks 反链 / graph 链接图谱。"
            "全文检索返回标题/正文/标签三路命中的片段。"
        ),
    )
    async def wiki_search(
        vault_id: str,
        mode: str = "search",
        q: str | None = None,
        path: str | None = None,
        limit: int | None = None,
    ) -> dict:
        try:
            lim = limit or s.max_result_items
            if mode == "search":
                if not q:
                    raise ToolError("mode=search 需要 q 参数")
                data = await ctx.client.get(
                    f"/wiki/vaults/{vault_id}/explore/search", params={"q": q}
                )
                results = (data or [])[:lim]
                return {"ok": True, "mode": mode, "count": len(results), "results": results}
            if mode == "backlinks":
                if not path:
                    raise ToolError("mode=backlinks 需要 path 参数")
                rel = wiki_ad.validate_rel_path(path)
                data = await ctx.client.get(
                    f"/wiki/vaults/{vault_id}/explore/backlinks", params={"path": rel}
                )
                results = (data or [])[:lim]
                return {"ok": True, "mode": mode, "path": rel, "count": len(results), "backlinks": results}
            if mode == "graph":
                data = await ctx.client.get(f"/wiki/vaults/{vault_id}/explore/graph")
                nodes = (data or {}).get("nodes", [])
                edges = (data or {}).get("edges", [])
                return {
                    "ok": True,
                    "mode": mode,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "nodes": nodes[:lim],
                    "edges": edges[: lim * 3],
                    "truncated": len(nodes) > lim,
                }
            raise ToolError(f"未知 mode: {mode}（可用 search/backlinks/graph）")
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- write tools (P2) ----------------

    @mcp.tool(
        name="wiki_create_page",
        description=(
            "新建 Wiki 页（一步执行）。path 为库内 .md 相对路径；页面已存在时后端返回 409，"
            "工具会提示改用 wiki_write_page 覆盖。dry_run=true 仅预览。"
        ),
    )
    async def wiki_create_page(
        vault_id: str,
        path: str,
        content: str,
        dry_run: bool = False,
    ) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            preview = {
                "vault_id": vault_id,
                "path": rel,
                "title": wiki_ad.page_title_from_path(rel),
                "content_chars": len(content),
                "create_new": True,
            }

            async def execute(_args: dict) -> dict:
                try:
                    page = await ctx.client.post(
                        f"/wiki/vaults/{vault_id}/pages", json={"path": rel, "content": content}
                    )
                except StudioError as exc:
                    if exc.status == 409:
                        raise ToolError(
                            f"页面已存在: {rel}（已存在页请用 wiki_write_page 覆盖写入）"
                        ) from exc
                    raise
                return {"ok": True, "path": page.get("path", rel), "created": True}

            return await confirm_gate(
                ctx, "wiki_create_page", {"dry_run": dry_run}, preview, execute, force=False
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="wiki_write_page",
        description=(
            "覆盖写入 Wiki 页（强制确认）。流程：路径预校验 → 读取旧内容 → "
            "已存在且 overwrite=false 时返回 diff 预览并要求确认（不盲覆盖）→ "
            "加写锁(holder=mcp-bot@mcp) → PUT 全量内容 → 显式 commit（message 可配）→ 释放锁。"
            "新建页请用 wiki_create_page。"
        ),
    )
    async def wiki_write_page(
        vault_id: str,
        path: str,
        content: str,
        overwrite: bool = False,
        commit: bool = True,
        message: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            existing = await get_page(ctx, vault_id, rel)
            exists = existing is not None
            old_content = (existing or {}).get("content") or ""
            diff = unified_diff(old_content, content, rel) if exists else None

            preview = {
                "vault_id": vault_id,
                "path": rel,
                "title": wiki_ad.page_title_from_path(rel),
                "exists": exists,
                "old_chars": len(old_content),
                "new_chars": len(content),
                "overwrite": overwrite,
                "commit": commit,
                "message": message or "(auto)",
                "diff": diff,
            }
            if exists and not overwrite:
                preview["note"] = "目标页已存在且 overwrite=false：确认令牌仅在你重新以 overwrite=true 调用时生效"

            async def execute(args: dict) -> dict:
                if exists and not args.get("overwrite", False):
                    raise ToolError(
                        "目标页已存在且本次参数 overwrite=false，已拒绝写入；"
                        "如确认覆盖请带 overwrite=true 重新获取确认后执行"
                    )
                result = await write_page(
                    ctx,
                    vault_id,
                    rel,
                    args.get("content", content),
                    commit=args.get("commit", commit),
                    message=args.get("message") or message,
                )
                result["overwritten"] = exists
                return result

            return await confirm_gate(
                ctx,
                "wiki_write_page",
                {
                    "vault_id": vault_id,
                    "path": rel,
                    "content": content,
                    "overwrite": overwrite,
                    "commit": commit,
                    "message": message,
                    "confirm_token": confirm_token,
                    "dry_run": dry_run,
                },
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="wiki_history",
        description=(
            "Wiki 页历史。action=list 提交历史（commit/author/date/message）/ diff 查看某提交相对前一版"
            "（或 compare 指定版本）的 unified diff / revert 回滚到指定 commit"
            "（覆盖性操作，需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true + 强制确认）。"
        ),
    )
    async def wiki_history(
        vault_id: str,
        path: str,
        action: str = "list",
        commit: str | None = None,
        compare: str | None = None,
        limit: int = 50,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            base = f"/wiki/vaults/{vault_id}/history"
            if action == "list":
                entries = await ctx.client.get(base, params={"path": rel, "limit": limit})
                return {"ok": True, "path": rel, "count": len(entries or []), "entries": entries or []}
            if action == "diff":
                if not commit:
                    raise ToolError("action=diff 需要 commit 参数")
                data = await ctx.client.get(
                    f"{base}/diff", params={"path": rel, "commit": commit, "compare": compare}
                )
                return {"ok": True, "path": rel, "commit": commit, "compare": compare, **(data or {})}
            if action == "revert":
                if not commit:
                    raise ToolError("action=revert 需要 commit 参数")
                if not s.allow_destructive:
                    raise ToolError(
                        "revert 会用历史版本覆盖当前页，需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true 才会执行"
                    )
                preview = {
                    "action": "revert",
                    "path": rel,
                    "commit": commit,
                    "recoverable": False,
                    "warning": "回滚将用历史版本覆盖当前页内容",
                }

                async def execute_revert(_args: dict) -> dict:
                    result = await ctx.client.post(f"{base}/revert", json={"path": rel, "commit": commit})
                    return {"ok": True, "path": rel, "commit": commit, "result": result}

                return await confirm_gate(
                    ctx,
                    "wiki_history",
                    {
                        "vault_id": vault_id,
                        "path": rel,
                        "action": action,
                        "commit": commit,
                        "compare": compare,
                        "limit": limit,
                        "confirm_token": confirm_token,
                        "dry_run": dry_run,
                    },
                    preview,
                    execute_revert,
                    force=True,
                )
            raise ToolError(f"未知 action: {action}（可用 list/diff/revert）")
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc
