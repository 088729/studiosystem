"""Case-domain tools (P0 read + P1 write)."""

from __future__ import annotations

import logging

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import case as case_ad
from ..context import AppContext
from ..policy.flow import confirm_gate

logger = logging.getLogger(__name__)


def _err(exc) -> ToolError:
    return ToolError(str(exc))


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="case_list_folders",
        description="列出用例导图文件夹树（平铺列表，含 parent_id/depth，可自行组装层级）。",
    )
    async def case_list_folders() -> dict:
        try:
            data = await ctx.client.get("/case/folders/tree")
            items = data.get("items", [])
            return {"ok": True, "count": len(items), "folders": items}
        except Exception as exc:  # StudioError
            raise _err(exc) from exc

    @mcp.tool(
        name="case_list_maps",
        description=(
            "列出用例导图。可按 folder_id 过滤、关键词 q 搜索；list_all=true 看全部。"
            "返回每个导图的 id/标题/当前版本号/所属文件夹，供 case_get_map 使用。"
        ),
    )
    async def case_list_maps(
        folder_id: str | None = None,
        q: str | None = None,
        list_all: bool = False,
        limit: int | None = None,
    ) -> dict:
        try:
            params = {"list_all": list_all}
            if folder_id:
                params["folder_id"] = folder_id
            if q:
                params["q"] = q
            data = await ctx.client.get("/case/maps", params=params)
            items = data.get("items", [])
            kept, has_more = case_ad.trim_items(items, limit or s.max_result_items)
            return {
                "ok": True,
                "count": len(kept),
                "total": len(items),
                "has_more": has_more,
                "maps": kept,
            }
        except Exception as exc:
            raise _err(exc) from exc

    @mcp.tool(
        name="case_get_map",
        description=(
            "读取一张用例导图并转成文本大纲（每行一个节点，带 [uid] 与缩进），"
            "避免直接给模型一坨 JSON。source: published=正式版(默认) / draft=草稿 / version:N=指定版本。"
            "同时返回 current_version、锁状态等元信息。P1 的 case_edit_map 用这里的 uid 定位节点。"
        ),
    )
    async def case_get_map(
        map_id: str,
        source: str | None = None,
        version: int | None = None,
    ) -> dict:
        try:
            detail = await ctx.client.get(f"/case/maps/{map_id}")
            src = source or s.case_source
            meta = {
                "id": detail.get("id"),
                "title": detail.get("title"),
                "current_version": detail.get("current_version"),
                "locked_by": detail.get("locked_by"),
                "folder_id": detail.get("folder_id"),
                "last_modified_at": str(detail.get("last_modified_at") or ""),
            }
            if version is not None:
                ver = await ctx.client.get(f"/case/maps/{map_id}/versions/{version}")
                tree = ver.get("root") or {}
                meta["source"] = f"version:{version}"
                meta["version_changelog"] = ver.get("changelog")
            elif src == "draft":
                tree = detail.get("temp_content") or {}
                meta["source"] = "draft"
            else:
                tree = detail.get("latest_root") or {}
                meta["source"] = "published"

            root_node = tree.get("root") if isinstance(tree, dict) else None
            if not root_node:
                return {
                    "ok": True,
                    "meta": meta,
                    "outline": "",
                    "node_count": 0,
                    "note": "该来源没有内容（可能尚未保存过此版本/草稿）",
                }
            return {
                "ok": True,
                "meta": meta,
                "outline": case_ad.outline(root_node),
                "node_count": case_ad.count_nodes(root_node),
            }
        except Exception as exc:
            raise _err(exc) from exc

    # ---------------- write tools (P1) ----------------

    @mcp.tool(
        name="case_create_map",
        description=(
            "新建用例导图。可传 outline（缩进文本大纲，2 空格一级）自动构树；"
            "不传则建单节点空导图。folder_id 可从 case_list_folders 获取。"
        ),
    )
    async def case_create_map(
        title: str,
        folder_id: str | None = None,
        outline: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        root_node = case_ad.outline_to_tree(title, outline) if outline else {
            "data": {"text": title, "uid": "root", "expand": True},
            "children": [],
        }
        root_data = {
            "root": root_node,
            "layout": "logicalStructure",
            "theme": {"template": "default", "config": {}},
            "view": {"transform": {"scale": 1, "x": 0, "y": 0}},
        }
        payload: dict = {"title": title, "root": root_data}
        if folder_id:
            payload["folder_id"] = folder_id

        async def execute(_args: dict) -> dict:
            created = await ctx.client.post("/case/maps", json=payload)
            return {"ok": True, "map": created, "node_count": case_ad.count_nodes(root_node)}

        preview = {"title": title, "folder_id": folder_id, "node_count": case_ad.count_nodes(root_node)}
        return await confirm_gate(ctx, "case_create_map", {"dry_run": dry_run}, preview, execute, force=False)

    @mcp.tool(
        name="case_edit_map",
        description=(
            "用例导图主写入口：节点级 patch（add/update/delete/move，uid 从 case_get_map 的大纲获取），"
            "内部完成 加锁→读→版本CAS→snapshot→解锁 的完整闭环，避免 1 分钟锁 TTL 与草稿异步陷阱。\n"
            "默认两阶段确认：首次调用返回变更预览 + confirm_token，带 token 再次调用才真正写入。"
        ),
    )
    async def case_edit_map(
        map_id: str,
        patches: list[dict],
        changelog: str = "MCP 编辑",
        source: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            detail = await ctx.client.get(f"/case/maps/{map_id}")
            src = source or s.case_source
            tree = (detail.get("temp_content") or {}) if src == "draft" else (detail.get("latest_root") or {})
            base_root = tree.get("root")
            if not base_root:
                raise ToolError(f"导图 {map_id} 没有{src}内容，无法在此基础上修改")
            base_version = detail.get("current_version")
            locked_by = detail.get("locked_by")

            new_root, summary = case_ad.apply_patches(base_root, patches)
            new_tree = {**tree, "root": new_root}
            preview = {
                "map_id": map_id,
                "base_version": base_version,
                "locked_by": locked_by,
                "source": src,
                "changes": summary,
                "changelog": changelog,
                "new_outline_head": "\n".join(case_ad.outline(new_root).splitlines()[:20]),
            }

            async def execute(_args: dict) -> dict:
                # 1. lock (423 → readable error)
                try:
                    await ctx.client.post(f"/case/maps/{map_id}/lock")
                except Exception as exc:
                    if getattr(exc, "status", None) == 423:
                        raise ToolError(f"导图被 {locked_by or '他人'} 锁定，请稍后重试") from exc
                    raise

                heartbeat_stop = False

                async def _heartbeat() -> None:
                    import asyncio

                    while not heartbeat_stop:
                        await asyncio.sleep(25)
                        try:
                            await ctx.client.post(f"/case/maps/{map_id}/lock")
                        except Exception as hb_exc:  # heartbeat best-effort
                            logger.warning("case lock heartbeat failed: %s", hb_exc)

                import asyncio

                hb_task = asyncio.create_task(_heartbeat())
                try:
                    # 2. version CAS (application-level; backend has no If-Match)
                    fresh = await ctx.client.get(f"/case/maps/{map_id}")
                    if fresh.get("current_version") != base_version:
                        raise ToolError(
                            f"导图已被他人从版本 {base_version} 改到 {fresh.get('current_version')}，"
                            "已放弃保存以避免覆盖；请重新 case_get_map 后再改"
                        )
                    # 3. snapshot (synchronous, whole-tree)
                    result = await ctx.client.post(
                        f"/case/maps/{map_id}/snapshot",
                        json={"root": new_tree, "changelog": changelog, "overwrite": False},
                    )
                    return {
                        "ok": True,
                        "map_id": map_id,
                        "version_no": result.get("version_no"),
                        "changelog": result.get("changelog"),
                        "changes": summary,
                    }
                finally:
                    heartbeat_stop = True
                    hb_task.cancel()
                    try:
                        await ctx.client.delete(f"/case/maps/{map_id}/lock")
                    except Exception as rel_exc:  # release best-effort
                        logger.warning("case lock release failed: %s", rel_exc)

            return await confirm_gate(
                ctx,
                "case_edit_map",
                {
                    "map_id": map_id,
                    "patches": patches,
                    "changelog": changelog,
                    "source": src,
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
            raise _err(exc) from exc

    @mcp.tool(
        name="case_save_draft",
        description=(
            "只写草稿（temp_content），用于长会话中间态。注意后端是异步保存（BackgroundTasks），"
            "写完立刻读可能读到旧值；正式保存请用 case_edit_map。"
        ),
    )
    async def case_save_draft(
        map_id: str,
        patches: list[dict] | None = None,
        title: str | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if patches is None and title is None:
                raise ToolError("patches 与 title 至少传一个")

            payload: dict = {}
            if title is not None:
                payload["title"] = title
            node_count = None
            if patches is not None:
                detail = await ctx.client.get(f"/case/maps/{map_id}")
                draft = detail.get("temp_content") or detail.get("latest_root") or {}
                base_root = draft.get("root")
                if not base_root:
                    raise ToolError("导图没有可编辑内容")
                new_root, summary = case_ad.apply_patches(base_root, patches)
                payload["temp_content"] = {**draft, "root": new_root}
                node_count = case_ad.count_nodes(new_root)
                preview = {"map_id": map_id, "title": title, "changes": summary}
            else:
                preview = {"map_id": map_id, "title": title, "changes": None}

            async def execute(_args: dict) -> dict:
                await ctx.client.patch(f"/case/maps/{map_id}", json=payload)
                return {
                    "ok": True,
                    "map_id": map_id,
                    "note": "草稿已提交（后端异步保存，立即读取可能仍是旧值）",
                    "node_count": node_count,
                }

            return await confirm_gate(
                ctx,
                "case_save_draft",
                {
                    "map_id": map_id,
                    "patches": patches,
                    "title": title,
                    "confirm_token": confirm_token,
                    "dry_run": dry_run,
                },
                preview,
                execute,
                force=False,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise _err(exc) from exc

    @mcp.tool(
        name="case_versions",
        description=(
            "导图版本：默认 list 返回版本历史（版本号/changelog/操作人）；"
            "action=rollback 回滚到指定版本（不可逆，强制确认）。"
        ),
    )
    async def case_versions(
        map_id: str,
        action: str = "list",
        version_no: int | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if action == "list":
                data = await ctx.client.get(f"/case/maps/{map_id}/versions")
                return {"ok": True, "total": data.get("total"), "versions": data.get("items", [])}
            if action == "rollback":
                if version_no is None:
                    raise ToolError("rollback 需要 version_no（先 action=list 查看）")
                if not s.allow_destructive:
                    raise ToolError("rollback 属于不可逆操作，需要 STUDIO_MCP_ALLOW_DESTRUCTIVE=true 才会执行")
                preview = {"action": "rollback", "map_id": map_id, "version_no": version_no}

                async def execute(_args: dict) -> dict:
                    result = await ctx.client.post(
                        f"/case/maps/{map_id}/rollback", json={"version_no": version_no}
                    )
                    return {
                        "ok": True,
                        "rolled_back_to": result.get("version_no"),
                        "changelog": result.get("changelog"),
                    }

                return await confirm_gate(
                    ctx,
                    "case_versions",
                    {
                        "map_id": map_id,
                        "action": action,
                        "version_no": version_no,
                        "confirm_token": confirm_token,
                        "dry_run": dry_run,
                    },
                    preview,
                    execute,
                    force=True,
                )
            raise ToolError(f"未知 action: {action}（可用 list/rollback）")
        except ToolError:
            raise
        except Exception as exc:
            raise _err(exc) from exc
