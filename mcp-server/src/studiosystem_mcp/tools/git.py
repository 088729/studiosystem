"""Git-sync domain (P2): vault status / page history & revert / pull / push / commit / reindex.

Every write here goes through the confirmation gate; `page_revert` and
`vault_push` additionally require STUDIO_MCP_ALLOW_DESTRUCTIVE=true because
they overwrite remote or local state in ways that cannot be undone from here.
"""

from __future__ import annotations

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import wiki as wiki_ad
from ..context import AppContext
from ..policy.flow import confirm_gate


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    def _vault(vault_id: str | None) -> str:
        vid = vault_id or s.default_vault_id
        if not vid:
            raise ToolError("缺少 vault_id，且未配置 STUDIO_MCP_DEFAULT_VAULT_ID")
        return vid

    @mcp.tool(
        name="vault_status",
        description=(
            "单个 Wiki 库的 git 状态：未提交变更(changes)、文档数、索引重建状态。"
            "vault_id 缺省取 STUDIO_MCP_DEFAULT_VAULT_ID。"
        ),
    )
    async def vault_status(vault_id: str | None = None) -> dict:
        try:
            vid = _vault(vault_id)
            data = await ctx.client.get(f"/wiki/vaults/{vid}")
            return {
                "ok": True,
                "vault_id": vid,
                "name": data.get("name"),
                "status": data.get("status"),
                "changes": data.get("changes"),
                "doc_count": data.get("doc_count"),
                "rebuild": data.get("rebuild"),
                "remote_url": data.get("remote_url"),
                "default_branch": data.get("default_branch"),
            }
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="page_history",
        description="Wiki 页的 git 提交历史（commit/author/date/message），默认最近 50 条。",
    )
    async def page_history(vault_id: str, path: str, limit: int = 50) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            entries = await ctx.client.get(
                f"/wiki/vaults/{vault_id}/history", params={"path": rel, "limit": limit}
            )
            return {"ok": True, "path": rel, "count": len(entries or []), "entries": entries or []}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="page_diff",
        description="查看 Wiki 页某提交相对前一版（或 compare 指定提交）的 unified diff。",
    )
    async def page_diff(vault_id: str, path: str, commit: str, compare: str | None = None) -> dict:
        try:
            rel = wiki_ad.validate_rel_path(path)
            data = await ctx.client.get(
                f"/wiki/vaults/{vault_id}/history/diff",
                params={"path": rel, "commit": commit, "compare": compare},
            )
            return {"ok": True, "path": rel, "commit": commit, "compare": compare, **(data or {})}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="page_revert",
        description=(
            "把 Wiki 页回滚到指定 commit（用历史版本覆盖当前页，不可从本工具撤销）。"
            "需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true + 强制确认。"
        ),
    )
    async def page_revert(
        vault_id: str,
        path: str,
        commit: str,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if not s.allow_destructive:
                raise ToolError(
                    "page_revert 会用历史版本覆盖当前页，需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true 才会执行"
                )
            rel = wiki_ad.validate_rel_path(path)
            preview = {
                "vault_id": vault_id,
                "path": rel,
                "commit": commit,
                "recoverable": False,
                "warning": "回滚将用历史版本覆盖当前页内容",
            }

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(
                    f"/wiki/vaults/{vault_id}/history/revert", json={"path": rel, "commit": commit}
                )
                return {"ok": True, "path": rel, "commit": commit, "result": result}

            return await confirm_gate(
                ctx,
                "page_revert",
                {
                    "vault_id": vault_id,
                    "path": rel,
                    "commit": commit,
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
        name="vault_pull",
        description=(
            "从远程拉取 Wiki 库并增量重建索引（强制确认）。远程冲突时返回冲突文件列表，"
            "需人工在库内解决后再推送。"
        ),
    )
    async def vault_pull(
        vault_id: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            vid = _vault(vault_id)
            preview = {"vault_id": vid, "action": "pull", "note": "拉取远程提交并增量重建索引"}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(f"/wiki/vaults/{vid}/pull")
                return {"ok": True, "vault_id": vid, "result": result}

            return await confirm_gate(
                ctx,
                "vault_pull",
                {"vault_id": vault_id, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="vault_push",
        description=(
            "把 Wiki 库本地提交推送到远程（不可从本工具撤销，需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true + 强制确认）。"
            "推送前建议先用 vault_status 确认 changes 已提交。"
        ),
    )
    async def vault_push(
        vault_id: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if not s.allow_destructive:
                raise ToolError(
                    "vault_push 会把本地提交推送到远程，需 STUDIO_MCP_ALLOW_DESTRUCTIVE=true 才会执行"
                )
            vid = _vault(vault_id)
            preview = {"vault_id": vid, "action": "push", "recoverable": False, "note": "推送后远程历史与本地一致"}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(f"/wiki/vaults/{vid}/push")
                return {"ok": True, "vault_id": vid, "result": result}

            return await confirm_gate(
                ctx,
                "vault_push",
                {"vault_id": vault_id, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="vault_commit",
        description="把 Wiki 库当前未提交变更做成一个 git 提交（强制确认，message 可配）。",
    )
    async def vault_commit(
        message: str,
        vault_id: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            vid = _vault(vault_id)
            preview = {"vault_id": vid, "message": message}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(
                    f"/wiki/vaults/{vid}/pages/commit", json={"message": message}
                )
                return {"ok": True, "vault_id": vid, "commit": result}

            return await confirm_gate(
                ctx,
                "vault_commit",
                {
                    "message": message,
                    "vault_id": vault_id,
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
        name="wiki_reindex",
        description=(
            "触发 Wiki 库全文索引重建（异步任务，立即返回 running）。"
            "重建期间再次调用会提示「索引重建中」；用 vault_status 的 rebuild 字段轮询进度。"
        ),
    )
    async def wiki_reindex(vault_id: str | None = None) -> dict:
        try:
            vid = _vault(vault_id)
            result = await ctx.client.post(f"/wiki/vaults/{vid}/rebuild-index")
            return {"ok": True, "vault_id": vid, **(result or {})}
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc
