"""Tool registration router: domain modules register through the guard."""

from ..context import AppContext
from ..policy.guard import ToolMeta
from . import admin, analytics, case, collab, focus, git, habits, system, task, wiki, workflow

# Every tool's guard metadata, keyed by tool name.
TOOL_METAS = [
    # system (always on)
    ToolMeta("studio_status", "system", True),
    ToolMeta("studio_capabilities", "system", True),
    ToolMeta("whoami", "system", True),
    # case
    ToolMeta("case_list_folders", "case", True),
    ToolMeta("case_list_maps", "case", True),
    ToolMeta("case_get_map", "case", True),
    ToolMeta("case_create_map", "case", False),
    ToolMeta("case_edit_map", "case", False),
    ToolMeta("case_save_draft", "case", False),
    # rollback 子操作在 flow 内额外要求 allow_destructive（list 不受影响）
    ToolMeta("case_versions", "case", False),
    # task
    ToolMeta("task_list_context", "task", True),
    ToolMeta("task_list_tasks", "task", True),
    ToolMeta("task_get_task", "task", True),
    ToolMeta("task_create", "task", False),
    ToolMeta("task_update", "task", False),
    # purge 子操作在 flow 内额外要求 allow_destructive（soft/restore 不受影响）
    ToolMeta("task_delete", "task", False),
    ToolMeta("task_batch", "task", False),
    # wiki
    ToolMeta("wiki_list_vaults", "wiki", True),
    ToolMeta("wiki_tree", "wiki", True),
    ToolMeta("wiki_read_page", "wiki", True),
    ToolMeta("wiki_search", "wiki", True),
    ToolMeta("wiki_create_page", "wiki", False),
    # 覆盖类写：强制确认；已存在且 overwrite=false 时拒绝盲覆盖
    ToolMeta("wiki_write_page", "wiki", False),
    # revert 子操作在 flow 内额外要求 allow_destructive（list/diff 不受影响）
    ToolMeta("wiki_history", "wiki", False),
    # analytics (P1)
    ToolMeta("task_overview", "analytics", True),
    ToolMeta("task_summary_markdown", "analytics", True),
    # focus (P1 read + P2 write)
    ToolMeta("focus_status", "focus", True),
    ToolMeta("focus_report", "focus", True),
    ToolMeta("focus_start", "focus", False),
    ToolMeta("focus_pause", "focus", False),
    ToolMeta("focus_resume", "focus", False),
    ToolMeta("focus_finish", "focus", False),
    ToolMeta("focus_abandon", "focus", False),
    # habits (P1 read + P2 write)
    ToolMeta("habit_today", "habits", True),
    ToolMeta("habit_week", "habits", True),
    ToolMeta("habit_stats", "habits", True),
    ToolMeta("habit_checkin", "habits", False),
    ToolMeta("habit_skip", "habits", False),
    ToolMeta("habit_un_checkin", "habits", False),
    # git (P2)
    ToolMeta("vault_status", "git", True),
    ToolMeta("page_history", "git", True),
    ToolMeta("page_diff", "git", True),
    # revert/push 需 allow_destructive（在 flow 内校验）
    ToolMeta("page_revert", "git", False),
    ToolMeta("vault_pull", "git", False),
    ToolMeta("vault_push", "git", False),
    ToolMeta("vault_commit", "git", False),
    ToolMeta("wiki_reindex", "git", False),
    # collab (P2)
    ToolMeta("task_comment", "collab", False),
    ToolMeta("calendar_range", "collab", True),
    ToolMeta("pending_reminders", "collab", True),
    ToolMeta("reminder_ack", "collab", False),
    ToolMeta("share_members", "collab", False),
    # workflow (P2)
    ToolMeta("generate_wiki_from_tasks", "workflow", False),
    ToolMeta("generate_wiki_from_case", "workflow", False),
    ToolMeta("case_outline_to_tasks", "workflow", False),
    # admin (P3, 默认关闭：需 ALLOW_ADMIN=true + READ_ONLY=false + 后端 sys:manage)
    ToolMeta("admin_user_list", "admin", True),
    ToolMeta("admin_role_list", "admin", True),
    ToolMeta("admin_permission_list", "admin", True),
    ToolMeta("admin_user_create", "admin", False),
    ToolMeta("admin_user_update", "admin", False),
    ToolMeta("admin_user_delete", "admin", False),
    ToolMeta("admin_batch_permissions", "admin", False),
    ToolMeta("admin_role_create", "admin", False),
    ToolMeta("admin_role_update", "admin", False),
    ToolMeta("admin_role_delete", "admin", False),
    ToolMeta("admin_permission_create", "admin", False),
    ToolMeta("admin_permission_delete", "admin", False),
]

REGISTER_FNS = {
    "system": system.register,
    "case": case.register,
    "task": task.register,
    "wiki": wiki.register,
    "analytics": analytics.register,
    "focus": focus.register,
    "habits": habits.register,
    "git": git.register,
    "collab": collab.register,
    "workflow": workflow.register,
    "admin": admin.register,
}


def register_tools(mcp, ctx: AppContext) -> None:
    """Register enabled domains' tools, honoring the guard per tool.

    Domains are registered wholesale, then tools rejected by the guard
    (deny-list / allow-list / read-only / destructive) are removed so they
    never appear in `tools/list`.

    The `admin` domain is triple-gated (§9): it only registers when
    `ALLOW_ADMIN=true` AND `READ_ONLY=false`; the backend still enforces
    `sys:manage` on every admin endpoint.
    """
    admin_enabled = ctx.settings.allow_admin and not ctx.settings.read_only
    enabled_domains = {m.domain for m in TOOL_METAS if ctx.guard.register(m)}
    rejected = [
        m.name
        for m in TOOL_METAS
        if not ctx.guard.is_registered(m.name) and not (m.domain == "admin" and not admin_enabled)
    ]

    for domain in sorted(enabled_domains):
        if domain == "admin" and not admin_enabled:
            continue
        if register_fn := REGISTER_FNS.get(domain):
            register_fn(mcp, ctx)

    for name in rejected:
        meta = next(m for m in TOOL_METAS if m.name == name)
        if meta.domain in enabled_domains:  # only remove what was actually registered
            try:
                mcp.remove_tool(name)
            except Exception:  # pragma: no cover - defensive
                pass
