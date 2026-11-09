"""Task-domain tools (P0 read + P1 write)."""

from __future__ import annotations

import asyncio

from mcp.server.mcpserver.tools.base import ToolError

from ..adapters import case as case_ad
from ..adapters import task as task_ad
from ..context import AppContext
from ..policy.flow import confirm_gate


def register(mcp, ctx: AppContext) -> None:
    s = ctx.settings

    @mcp.tool(
        name="task_list_context",
        description=(
            "一次性返回任务模块的上下文：清单（含收集箱/共享标记）、标签、已保存筛选器。"
            "后续 task_list_tasks / task_create 需要 list_id、tag、filter_id 时从这里选。"
        ),
    )
    async def task_list_context() -> dict:
        try:
            lists, tags, filters = await asyncio.gather(
                ctx.client.get("/task/lists"),
                ctx.client.get("/task/tags"),
                ctx.client.get("/task/filters"),
            )
            return {
                "ok": True,
                "lists": lists.get("items", []),
                "tags": tags.get("items", []),
                "filters": filters.get("items", []),
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_list_tasks",
        description=(
            "查询任务。list_id 过滤清单（可从 task_list_context 获取；\"inbox\" 为收集箱），"
            "smart 智能清单，status=todo/done，priority=0-3，tag 标签名，q 关键词。"
            "默认按 STUDIO_MCP_MAX_RESULT_ITEMS 裁剪并返回 has_more。"
        ),
    )
    async def task_list_tasks(
        list_id: str | None = None,
        smart: str | None = None,
        filter_id: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        tag: str | None = None,
        q: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        try:
            params: dict = {"tz_offset_minutes": s.tz_offset_minutes, "offset": offset}
            for key, val in (
                ("list_id", list_id),
                ("smart", smart),
                ("filter_id", filter_id),
                ("status", status),
                ("priority", priority),
                ("tag", tag),
                ("q", q),
            ):
                if val is not None:
                    params[key] = val
            data = await ctx.client.get("/task/tasks", params=params)
            items = data.get("items", [])
            kept, has_more = case_ad.trim_items(items, limit or s.max_result_items)
            return {
                "ok": True,
                "count": len(kept),
                "total": len(items),
                "has_more": has_more,
                "tasks": [task_ad.format_task_line(t) for t in kept],
                "tasks_raw": kept,
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_get_task",
        description=(
            "任务详情：完整字段 + 子任务 + 关联用例导图标题与节点文本"
            "（task.case_map_id / case_node_id 反查）。"
        ),
    )
    async def task_get_task(task_id: str) -> dict:
        try:
            task = await ctx.client.get(f"/task/tasks/{task_id}")
            return {"ok": True, "task": task}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    # ---------------- write tools (P1) ----------------

    @mcp.tool(
        name="task_create",
        description=(
            "创建任务。支持 quick-add 自然语言：「写登录用例 @明天 !高 ~回归 #登录」"
            "（@日期支持 今天/明天/后天/下周/周末/N月N日/ISO；!优先级 无/低/中/高 或 0-3；"
            "#清单 模糊匹配，未命中落收集箱）。也可直接传结构化字段。"
            "传 idempotency_key 可在 5 分钟内防重复创建。"
        ),
    )
    async def task_create(
        text: str | None = None,
        title: str | None = None,
        list_id: str | None = None,
        list_name: str | None = None,
        priority: int | None = None,
        due_at: str | None = None,
        tags: list[str] | None = None,
        note: str | None = None,
        parent_id: str | None = None,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if idempotency_key:
                cached = ctx.idempotency.get(idempotency_key)
                if cached is not None:
                    return {**cached, "idempotent_replay": True}

            payload: dict = {"priority": 0, "tags": []}
            if text:
                try:
                    fields = task_ad.parse_quick_add(text)
                except ValueError as exc:
                    raise ToolError(str(exc)) from exc
                payload["title"] = fields["title"]
                if fields.get("due_at"):
                    payload["due_at"] = fields["due_at"]
                if fields.get("priority") is not None:
                    payload["priority"] = fields["priority"]
                if fields.get("tags"):
                    payload["tags"] = fields["tags"]
                if fields.get("list_name") and not list_id and not list_name:
                    list_name = fields["list_name"]
            elif title:
                payload["title"] = title
            else:
                raise ToolError("text 与 title 至少传一个")

            # structured fields override quick-add
            if priority is not None:
                payload["priority"] = priority
            if due_at:
                payload["due_at"] = due_at
            if tags:
                payload["tags"] = tags
            if note:
                payload["note"] = note
            if parent_id:
                payload["parent_id"] = parent_id

            list_resolution = None
            if list_id:
                payload["list_id"] = None if list_id == "inbox" else list_id
                list_resolution = list_id
            elif list_name:
                lists = (await ctx.client.get("/task/lists")).get("items", [])
                match = next(
                    (lst for lst in lists if lst.get("name") == list_name),
                    None,
                ) or next(
                    (lst for lst in lists if list_name in lst.get("name", "")),
                    None,
                )
                if match:
                    payload["list_id"] = match["id"]
                    list_resolution = f"{list_name} → {match['id']}"
                else:
                    list_resolution = f"清单「{list_name}」未命中，落入收集箱"

            async def execute(_args: dict) -> dict:
                task = await ctx.client.post("/task/tasks", json=payload)
                result = {
                    "ok": True,
                    "task": task_ad.format_task_line(task),
                    "task_raw": task,
                    "list_resolution": list_resolution,
                }
                if idempotency_key:
                    ctx.idempotency.put(idempotency_key, result, ttl_seconds=300)
                return result

            preview = {
                "payload": {k: v for k, v in payload.items() if k != "tags" or v},
                "list_resolution": list_resolution,
            }
            return await confirm_gate(ctx, "task_create", {"dry_run": dry_run}, preview, execute, force=False)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_update",
        description=(
            "修改任务。普通字段 PATCH 语义（只有显式传的字段才更新）；"
            "action=complete/uncomplete 走 /complete 接口（status 不可直接 PATCH）；"
            "action=skip 跳过本次（重复任务）。clear_due=true 清除截止时间。"
        ),
    )
    async def task_update(
        task_id: str,
        title: str | None = None,
        note: str | None = None,
        priority: int | None = None,
        due_at: str | None = None,
        clear_due: bool = False,
        tags: list[str] | None = None,
        list_id: str | None = None,
        parent_id: str | None = None,
        action: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if action:
                if action == "complete":
                    preview = {"action": "complete", "task_id": task_id, "done": True}
                elif action == "uncomplete":
                    preview = {"action": "uncomplete", "task_id": task_id, "done": False}
                elif action == "skip":
                    preview = {"action": "skip", "task_id": task_id}
                else:
                    raise ToolError(f"未知 action: {action}（可用 complete/uncomplete/skip）")

                async def execute_action(_args: dict) -> dict:
                    if action == "skip":
                        task = await ctx.client.post(f"/task/tasks/{task_id}/skip")
                    else:
                        task = await ctx.client.post(
                            f"/task/tasks/{task_id}/complete", json={"done": action == "complete"}
                        )
                    return {"ok": True, "task": task_ad.format_task_line(task)}

                return await confirm_gate(
                    ctx, "task_update", {"dry_run": dry_run}, preview, execute_action, force=False
                )

            patch: dict = {}
            if title is not None:
                patch["title"] = title
            if note is not None:
                patch["note"] = note
            if priority is not None:
                if not 0 <= priority <= 3:
                    raise ToolError("priority 必须是 0-3")
                patch["priority"] = priority
            if clear_due:
                patch["due_at"] = None
            elif due_at is not None:
                patch["due_at"] = due_at
            if tags is not None:
                patch["tags"] = tags
            if parent_id is not None:
                patch["parent_id"] = parent_id
            if not patch and list_id is None:
                raise ToolError("没有可更新的字段（传字段或 action）")

            async def execute(_args: dict) -> dict:
                task = await ctx.client.patch(f"/task/tasks/{task_id}", json=patch)
                if list_id is not None:
                    task = await ctx.client.patch(
                        f"/task/tasks/{task_id}/move", json={"list_id": None if list_id == "inbox" else list_id}
                    )
                return {"ok": True, "task": task_ad.format_task_line(task)}

            return await confirm_gate(
                ctx, "task_update", {"dry_run": dry_run}, {"patch": patch, "move_to": list_id}, execute, force=False
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_delete",
        description=(
            "删除任务：mode=soft 软删（默认，可恢复）/ restore 恢复 / purge 物理清除（不可恢复，强制确认）。"
        ),
    )
    async def task_delete(
        task_id: str,
        mode: str = "soft",
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if mode == "soft":
                preview = {"mode": "soft", "task_id": task_id, "recoverable": True}

                async def execute_soft(_args: dict) -> dict:
                    await ctx.client.delete(f"/task/tasks/{task_id}")
                    return {"ok": True, "mode": "soft", "task_id": task_id, "recoverable": True}

                return await confirm_gate(ctx, "task_delete", {"dry_run": dry_run}, preview, execute_soft, force=False)
            if mode == "restore":
                preview = {"mode": "restore", "task_id": task_id}

                async def execute_restore(_args: dict) -> dict:
                    task = await ctx.client.post(f"/task/tasks/{task_id}/restore")
                    return {"ok": True, "task": task_ad.format_task_line(task)}

                return await confirm_gate(
                    ctx, "task_delete", {"dry_run": dry_run}, preview, execute_restore, force=False
                )
            if mode == "purge":
                if not s.allow_destructive:
                    raise ToolError("purge 物理清除不可恢复，需要 STUDIO_MCP_ALLOW_DESTRUCTIVE=true 才会执行")
                preview = {"mode": "purge", "task_id": task_id, "recoverable": False, "warning": "物理清除后无法恢复"}

                async def execute_purge(_args: dict) -> dict:
                    await ctx.client.delete(f"/task/tasks/{task_id}/purge")
                    return {"ok": True, "mode": "purge", "task_id": task_id}

                return await confirm_gate(
                    ctx,
                    "task_delete",
                    {"task_id": task_id, "mode": mode, "confirm_token": confirm_token, "dry_run": dry_run},
                    preview,
                    execute_purge,
                    force=True,
                )
            raise ToolError(f"未知 mode: {mode}（可用 soft/restore/purge）")
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="task_batch",
        description=(
            "批量操作任务（ids 从 task_list_tasks 获取）。action: complete/delete/move/priority/due/pin/tags，"
            "payload 按 action 传（如 move: {\"list_id\": \"l1\"}；priority: {\"priority\": 3}）。"
            "影响多条任务，默认强制确认。"
        ),
    )
    async def task_batch(
        ids: list[str],
        action: str,
        payload: dict | None = None,
        confirm_token: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        try:
            if not ids:
                raise ToolError("ids 不能为空")
            preview = {"ids": ids, "action": action, "payload": payload or {}, "affected": len(ids)}

            async def execute(_args: dict) -> dict:
                result = await ctx.client.post(
                    "/task/tasks/batch", json={"ids": ids, "action": action, "payload": payload or {}}
                )
                return {"ok": True, "result": result}

            return await confirm_gate(
                ctx,
                "task_batch",
                {"ids": ids, "action": action, "payload": payload, "confirm_token": confirm_token, "dry_run": dry_run},
                preview,
                execute,
                force=True,
            )
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(str(exc)) from exc
