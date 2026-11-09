"""MCP Prompts (P2): reusable, safety-constrained prompt templates.

Each prompt returns a plain-text system/user instruction pair the client can
feed to its model. They embed the same safety rules as the write tools
(preview diff before confirming) so a model following a prompt stays inside
the confirmation flow.
"""

from __future__ import annotations

from .context import AppContext

_SAFETY = (
    "安全约束：任何写入（改导图/写 Wiki 页/建任务/回滚）必须先用 dry_run=true 或在预览阶段查看 diff，"
    "确认无误后再带 confirm_token 执行；不可逆操作（purge/rollback/revert/push）还需要"
    " STUDIO_MCP_ALLOW_DESTRUCTIVE=true。绝不臆造 id，所有 id 从 list 工具获取。"
)


def register(mcp, ctx: AppContext) -> None:
    @mcp.prompt(
        name="weekly_report",
        description="从任务数据生成本周周报 Wiki 页的完整工作流提示词",
    )
    def weekly_report() -> str:
        return (
            "你是周报助手。按以下步骤生成本周任务周报：\n"
            "1. 用 task_overview 与 task_summary_markdown 取本周任务事实（range=week）。\n"
            "2. 用 generate_wiki_from_tasks(range=\"week\") 生成周报页；"
            "模板渲染后你可以先润色 content 再回传覆盖。\n"
            "3. 目标路径默认 reports/{date}.md；commit message 用「docs: 周报 <date> by MCP」。\n"
            + _SAFETY
        )

    @mcp.prompt(
        name="testcase_spec",
        description="把用例导图导出为 Wiki 规格文档的提示词",
    )
    def testcase_spec() -> str:
        return (
            "你是测试文档助手。步骤：\n"
            "1. 用 case_get_map 读取目标导图（文本大纲），确认结构。\n"
            "2. 用 generate_wiki_from_case 把导图导出为规格页"
            "（默认 testcase_spec.md.j2，含 frontmatter 与来源双链）。\n"
            "3. 导出后可按需补充前置条件/测试数据段落，再用 content 回传覆盖。\n"
            + _SAFETY
        )

    @mcp.prompt(
        name="retro",
        description="周复盘提示词：数据底稿 + 三个待填写板块",
    )
    def retro() -> str:
        return (
            "你是复盘引导者。步骤：\n"
            "1. 用 task_summary_markdown(range=\"week\") 与 focus_report 取本周任务/专注事实。\n"
            "2. 用 generate_wiki_from_tasks(template=\"retro.md.j2\") 生成复盘页。\n"
            "3. 引导用户填写「做得好/待改进/下周计划」三个板块后再覆盖写回。\n"
            + _SAFETY
        )

    @mcp.prompt(
        name="case_review",
        description="评审用例导图质量的提示词",
    )
    def case_review() -> str:
        return (
            "你是用例评审专家。步骤：\n"
            "1. 用 case_get_map 读取导图大纲。\n"
            "2. 检查：等价类是否有遗漏、异常场景是否覆盖、节点措辞是否可执行、层级是否过深（>5 层建议收敛）。\n"
            "3. 给出 case_edit_map 的 patches（add/update/delete/move）修改建议，"
            "先 dry_run 展示 diff 供人工确认。\n"
            + _SAFETY
        )

    @mcp.prompt(
        name="standup",
        description="站会要点提示词：昨日完成/今日计划/阻塞项",
    )
    def standup() -> str:
        return (
            "你是站会助手。步骤：\n"
            "1. 用 task_overview、task_list_tasks(status=\"done\")、task_list_tasks(status=\"todo\")、"
            "pending_reminders 收集事实。\n"
            "2. 输出三段：昨日完成（含 focus_report 专注时长）、今日计划（按优先级）、阻塞项（逾期/被锁/待他人）。\n"
            "3. 纯只读流程，不要触发任何写工具。\n"
        )
