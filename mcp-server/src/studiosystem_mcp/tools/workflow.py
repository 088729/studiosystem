"""Workflow domain (P2): cross-module compositions.

- generate_wiki_from_tasks: task summary → Jinja2 template → wiki page (+commit)
- generate_wiki_from_case: case map outline → testcase_spec template → wiki page
- case_outline_to_tasks: map leaf nodes → task creation with case back-references

Generation never blind-overwrites: it reads the target page first, shows a
unified diff and goes through the forced confirmation gate before locking /
PUT / commit (the same `write_page` flow as wiki_write_page).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import case as case_ad
from ..adapters import render as render_ad
from ..adapters import wiki as wiki_ad
from ..context import AppContext
from ..policy.flow import confirm_gate
from . import wiki as wiki_tools


def _today(tz_offset_minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=tz_offset_minutes)).date().isoformat()


def _resolve_vault(ctx: AppContext, vault_id: str | None) -> str:
    vid = vault_id or ctx.settings.default_vault_id
    if not vid:
        raise ToolError("缺少 vault_id，且未配置 STUDIO_MCP_DEFAULT_VAULT_ID")
    return vid


def _resolve_path(ctx: AppContext, path: str | None) -> str:
    raw = path or ctx.settings.default_wiki_path
    return wiki_ad.validate_rel_path(raw.replace("{date}", _today(ctx.settings.tz_offset_minutes)))


def _flow_args(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None or k in ("overwrite", "commit", "dry_run")}


async def _generate_page(
    ctx: AppContext,
    *,
    tool: str,
    vault_id: str | None,
    path: str | None,
    title: str,
    final_content: str,
    render_note: str,
    overwrite: bool,
    commit: bool,
    message: str | None,
    confirm_token: str | None,
    dry_run: bool,
) -> dict:
    """Shared tail of the generate_* tools: diff preview + gate + write_page."""
    vid = _resolve_vault(ctx, vault_id)
    rel = _resolve_path(ctx, path)
    existing = await wiki_tools.get_page(ctx, vid, rel)
    exists = existing is not None
    old_content = (existing or {}).get("content") or ""
    diff = wiki_tools.unified_diff(old_content, final_content, rel) if exists else None

    preview = {
        "vault_id": vid,
        "path": rel,
        "title": title,
        "exists": exists,
        "old_chars": len(old_content),
        "new_chars": len(final_content),
        "overwrite": overwrite,
        "commit": commit,
        "message": message or "(auto)",
        "render": render_note,
        "diff": diff,
    }
    if exists and not overwrite:
        preview["note"] = "目标页已存在且 overwrite=false：确认令牌仅在以 overwrite=true 重新调用时生效"

    async def execute(args: dict) -> dict:
        if exists and not args.get("overwrite", False):
            raise ToolError(
                "目标页已存在且本次参数 overwrite=false，已拒绝写入；"
                "如确认覆盖请带 overwrite=true 重新确认"
            )
        result = await wiki_tools.write_page(
            ctx,
            vid,
            rel,
            args.get("content", final_content),
            commit=args.get("commit", commit),
            message=args.get("message") or message,
        )
        result["title"] = title
        result["overwritten"] = exists
        return result

    return await confirm_gate(
        ctx,
        tool,
        _flow_args(
            vault_id=vault_id,
            path=path,
            content=final_content,
            overwrite=overwrite,
            commit=commit,
            message=message,
            confirm_token=confirm_token,
            dry_run=dry_run,
        ),
        preview,
        execute,
        force=True,
    )


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="generate_wiki_from_tasks",
        description=(
            "从任务摘要生成 Wiki 周报页。流程：POST /task/summary/preview 取事实底稿 → "
            "Jinja2 模板渲染（默认 weekly_report.md.j2；content 非空时跳过渲染直接用润色稿）→ "
            "读取目标页并给出 diff 预览 → 确认后加锁写入并显式 commit。"
            "vault_id/path 缺省取 STUDIO_MCP_DEFAULT_VAULT_ID / DEFAULT_WIKI_PATH（支持 {date} 占位）。"
        ),
    )
    async def generate_wiki_from_tasks(
        range: str = "week",
        vault_id: str | None = None,
        path: str | None = None,
        template: str = "weekly_report.md.j2",
        content: str | None = None,
        title: str | None = None,
        group_by: str | None = None,
        list_ids: list[str] | None = None,
        tags: list[str] | None = None,
        statuses: list[str] | None = None,
        overwrite: bool = False,
        commit: bool = True,
        message: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            body: dict = {"range": range, "tz_offset_minutes": s.tz_offset_minutes}
            for key, val in (("group_by", group_by), ("list_ids", list_ids), ("tags", tags), ("statuses", statuses)):
                if val is not None:
                    body[key] = val
            summary = await ctx.client.post("/task/summary/preview", json=body)

            date = _today(s.tz_offset_minutes)
            final_title = title or f"任务周报 {date}"
            groups = summary.get("groups") or []
            total = summary.get("total") or 0
            if content:
                final_content, render_note = content, "使用调用方提供的 content（润色稿），跳过模板渲染"
            else:
                env = render_ad.build_environment(s.templates_dir)
                try:
                    final_content = render_ad.render_template(
                        env,
                        template,
                        {
                            "title": final_title,
                            "date": date,
                            "range": range,
                            "groups": groups,
                            "total": total,
                            "markdown": summary.get("markdown") or "",
                        },
                    )
                    render_note = f"模板 {template} 渲染"
                except Exception as exc:
                    final_content = summary.get("markdown") or ""
                    render_note = f"模板 {template} 渲染失败（{exc}），退回 summary.markdown 底稿"

            return await _generate_page(
                ctx,
                tool="generate_wiki_from_tasks",
                vault_id=vault_id,
                path=path,
                title=final_title,
                final_content=final_content,
                render_note=render_note,
                overwrite=overwrite,
                commit=commit,
                message=message,
                confirm_token=confirm_token,
                dry_run=dry_run,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="generate_wiki_from_case",
        description=(
            "把用例导图导出为 Wiki 规格页（默认 testcase_spec.md.j2：frontmatter + 全节点清单 + 来源双链）。"
            "树来源遵循 STUDIO_MCP_CASE_SOURCE（published/draft）。写入流程同 generate_wiki_from_tasks。"
        ),
    )
    async def generate_wiki_from_case(
        map_id: str,
        vault_id: str | None = None,
        path: str | None = None,
        template: str = "testcase_spec.md.j2",
        content: str | None = None,
        title: str | None = None,
        overwrite: bool = False,
        commit: bool = True,
        message: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            detail = await ctx.client.get(f"/case/maps/{map_id}")
            tree = (detail.get("temp_content") or {}) if s.case_source == "draft" else (detail.get("latest_root") or {})
            root = tree.get("root")
            if not root:
                raise ToolError(f"导图 {map_id} 没有{s.case_source}内容，无法生成")
            map_title = detail.get("title") or map_id

            date = _today(s.tz_offset_minutes)
            final_title = title or f"{map_title} 用例规格"
            if content:
                final_content, render_note = content, "使用调用方提供的 content（润色稿），跳过模板渲染"
            else:
                nodes = [
                    {
                        "uid": case_ad.node_uid(node),
                        "text": case_ad.node_text(node) or "(空)",
                        "depth": depth,
                    }
                    for node, depth in case_ad.iter_nodes(root)
                ]
                env = render_ad.build_environment(s.templates_dir)
                try:
                    final_content = render_ad.render_template(
                        env,
                        template,
                        {
                            "title": final_title,
                            "map_id": map_id,
                            "map_title": map_title,
                            "date": date,
                            "nodes": nodes,
                        },
                    )
                    render_note = f"模板 {template} 渲染（{len(nodes)} 个节点）"
                except Exception as exc:
                    outline = case_ad.outline(root)
                    final_content = (
                        f"---\ntitle: \"{final_title}\"\nsource_case_map: \"{map_id}\"\n---\n\n"
                        f"# {final_title}\n\n```\n{outline}\n```\n"
                    )
                    render_note = f"模板 {template} 渲染失败（{exc}），退回大纲文本"

            return await _generate_page(
                ctx,
                tool="generate_wiki_from_case",
                vault_id=vault_id,
                path=path,
                title=final_title,
                final_content=final_content,
                render_note=render_note,
                overwrite=overwrite,
                commit=commit,
                message=message,
                confirm_token=confirm_token,
                dry_run=dry_run,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="case_outline_to_tasks",
        description=(
            "把导图叶子节点批量建成任务（回填 case_map_id/case_node_id 反链）。"
            "parent_uid 限定子树范围；list_id 缺省落收集箱。批量创建影响多条，默认强制确认。"
        ),
    )
    async def case_outline_to_tasks(
        map_id: str,
        parent_uid: str | None = None,
        list_id: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            detail = await ctx.client.get(f"/case/maps/{map_id}")
            tree = (detail.get("temp_content") or {}) if s.case_source == "draft" else (detail.get("latest_root") or {})
            root = tree.get("root")
            if not root:
                raise ToolError(f"导图 {map_id} 没有{s.case_source}内容")

            base = root
            if parent_uid:
                found = case_ad.find_node(root, parent_uid)
                if found is None:
                    raise ToolError(f"找不到节点 uid={parent_uid}")
                base = found

            leaves = [
                {"uid": case_ad.node_uid(node), "text": case_ad.node_text(node) or "(空)"}
                for node, _depth in case_ad.iter_nodes(base)
                if not (node.get("children") or [])
            ]
            if not leaves:
                raise ToolError("该范围没有叶子节点（容器节点不会转成任务）")

            preview = {
                "map_id": map_id,
                "scope": parent_uid or case_ad.node_uid(root) or "(整树)",
                "list_id": list_id or "inbox(收集箱)",
                "leaf_count": len(leaves),
                "titles_sample": [leaf["text"] for leaf in leaves[:10]],
                "backfill": {"case_map_id": map_id, "case_node_id": "<叶子节点 uid>"},
            }

            async def execute(_args: dict) -> dict:
                created, errors = [], []
                for leaf in leaves:
                    try:
                        task = await ctx.client.post(
                            "/task/tasks",
                            json={
                                "title": leaf["text"],
                                "list_id": list_id,
                                "case_map_id": map_id,
                                "case_node_id": leaf["uid"],
                            },
                        )
                        created.append({"task_id": task.get("id"), "title": leaf["text"], "node_uid": leaf["uid"]})
                    except Exception as exc:  # keep going; report per-leaf failures
                        errors.append({"node_uid": leaf["uid"], "title": leaf["text"], "error": str(exc)})
                return {
                    "ok": True,
                    "created_count": len(created),
                    "failed_count": len(errors),
                    "created": created,
                    "errors": errors,
                }

            return await confirm_gate(
                ctx,
                "case_outline_to_tasks",
                _flow_args(
                    map_id=map_id,
                    parent_uid=parent_uid,
                    list_id=list_id,
                    confirm_token=confirm_token,
                    dry_run=dry_run,
                ),
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc
