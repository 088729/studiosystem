"""搜索 / 反链 / 图谱数据组装。"""
import re
from typing import List, Optional

from app.models.wiki.wiki_link import WikiLink
from app.models.wiki.wiki_page import WikiPage
from app.models.wiki.wiki_vault import WikiVault

SNIPPET_RADIUS = 40
GRAPH_NODE_LIMIT = 500


def _regex_escape(q: str) -> str:
    return re.escape(q)


def _snippet(text: str, q: str) -> str:
    m = re.search(_regex_escape(q), text, flags=re.IGNORECASE)
    if not m:
        return text[: SNIPPET_RADIUS * 2]
    start = max(0, m.start() - SNIPPET_RADIUS)
    end = min(len(text), m.end() + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


async def search(vault: WikiVault, q: str, tag: Optional[str] = None, limit: int = 50) -> List[dict]:
    """标题命中排前、正文命中其次、标签命中补充；返回片段。"""
    vault_id = str(vault.id)
    q = (q or "").strip()
    results: List[dict] = []
    seen = set()

    async def _emit(page: WikiPage, kind: str, snippet: str):
        if page.path in seen:
            return
        seen.add(page.path)
        results.append({
            "path": page.path,
            "title": page.title,
            "kind": kind,
            "snippet": snippet,
            "tags": page.tags,
        })

    if tag:
        # 归一化：剥离 #/＃ 前缀，全角字符转半角，大小写不敏感精确匹配
        tag_norm = tag.lstrip("#＃").strip()
        tag_norm = tag_norm.translate(
            str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(0x5E)})
        ).lower()
        if tag_norm:
            async for page in WikiPage.find(
                {"vault_id": vault_id, "tags": {"$regex": f"^{_regex_escape(tag_norm)}$", "$options": "i"}}
            ).limit(limit):
                await _emit(page, "tag", "")

    if q:
        pattern = {"$regex": _regex_escape(q), "$options": "i"}
        title_hits = await WikiPage.find(
            WikiPage.vault_id == vault_id, {"title": pattern}
        ).limit(limit).to_list()
        for page in title_hits:
            await _emit(page, "title", "")

        body_hits = await WikiPage.find(
            WikiPage.vault_id == vault_id,
            {"body": pattern, "path": {"$nin": list(seen)}},
        ).limit(limit).to_list()
        for page in body_hits:
            await _emit(page, "body", _snippet(page.body, q))
    return results[:limit]


async def backlinks(vault: WikiVault, path: str) -> List[dict]:
    """反链列表：聚合引用方文档（标题 + 锚文本）。"""
    vault_id = str(vault.id)
    links = await WikiLink.find(
        WikiLink.vault_id == vault_id,
        WikiLink.dst_path == path,
        WikiLink.is_resolved == True,  # noqa: E712
    ).to_list()
    grouped: dict = {}
    for link in links:
        grouped.setdefault(link.src_path, []).append(link)
    out = []
    for src_path, src_links in grouped.items():
        page = await WikiPage.find_one(WikiPage.vault_id == vault_id, WikiPage.path == src_path)
        out.append({
            "path": src_path,
            "title": page.title if page else src_path,
            "aliases": [l.dst_alias for l in src_links],
        })
    return sorted(out, key=lambda x: x["title"].lower())


async def graph(vault: WikiVault) -> dict:
    """图谱节点边（仅 resolved），大库限制高度数节点。"""
    vault_id = str(vault.id)
    links = await WikiLink.find(
        WikiLink.vault_id == vault_id,
        WikiLink.is_resolved == True,  # noqa: E712
    ).to_list()
    degree: dict = {}
    for l in links:
        degree[l.src_path] = degree.get(l.src_path, 0) + 1
        degree[l.dst_path] = degree.get(l.dst_path, 0) + 1

    top_paths = sorted(degree, key=lambda p: -degree[p])[:GRAPH_NODE_LIMIT]
    keep = set(top_paths)
    nodes, edges = [], []
    for p in top_paths:
        page = await WikiPage.find_one(WikiPage.vault_id == vault_id, WikiPage.path == p)
        nodes.append({
            "path": p,
            "title": page.title if page else p,
            "tags": page.tags if page else [],
        })
    for l in links:
        if l.src_path in keep and l.dst_path in keep:
            edges.append({"src": l.src_path, "dst": l.dst_path, "type": l.link_type})
    return {"nodes": nodes, "edges": edges}
