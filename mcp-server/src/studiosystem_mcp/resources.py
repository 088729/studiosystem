"""Resources: studio://config, templates, and wildcard resource templates.

Resource templates (studio://case/maps/{map_id}/outline …) let clients `@`-reference
context without an extra tool call — cheaper than tools for static reads.
"""

from __future__ import annotations

import json

from .adapters import case as case_ad
from .context import AppContext


def register_resources(mcp, ctx: AppContext) -> None:
    @mcp.resource(
        "studio://config",
        name="studio-config",
        description="脱敏后的生效配置（能力域、只读状态、协议版本等）",
        mime_type="application/json",
    )
    async def studio_config() -> str:
        return json.dumps(
            {
                "protocol_versions": ctx.settings.version_list,
                "enabled_modules": sorted(ctx.settings.enabled_modules),
                "read_only": ctx.settings.read_only,
                "config": ctx.settings.redacted(),
            },
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource(
        "studio://case/maps/{map_id}/outline",
        name="case-map-outline",
        description="用例导图文本大纲（正式版），等价于 case_get_map(source='published')",
        mime_type="text/markdown",
    )
    async def case_map_outline(map_id: str) -> str:
        detail = await ctx.client.get(f"/case/maps/{map_id}")
        tree = detail.get("latest_root") or {}
        root = tree.get("root")
        if not root:
            return f"<!-- 导图 {map_id} 尚无正式版内容 -->"
        return case_ad.outline(root)

    @mcp.resource(
        "studio://wiki/vaults/{vault_id}/tree",
        name="wiki-vault-tree",
        description="Wiki 文档库目录树（文本形式）",
        mime_type="text/plain",
    )
    async def wiki_vault_tree(vault_id: str) -> str:
        from .adapters import wiki as wiki_ad

        nodes = await ctx.client.get(f"/wiki/vaults/{vault_id}/pages/tree")
        return wiki_ad.render_tree(nodes or [])

    @mcp.resource(
        "studio://wiki/vaults/{vault_id}/pages/{path}",
        name="wiki-page",
        description="Wiki 页面 Markdown 正文（path 为库内 .md 相对路径）",
        mime_type="text/markdown",
    )
    async def wiki_page(vault_id: str, path: str) -> str:
        from .adapters import wiki as wiki_ad

        rel = wiki_ad.validate_rel_path(path)
        data = await ctx.client.get(f"/wiki/vaults/{vault_id}/pages/content", params={"path": rel})
        return data.get("content") or ""
