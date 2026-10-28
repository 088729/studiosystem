"""Markdown 解析：frontmatter / 标题 / 标签 / 双链 / 纯文本正文（索引用）。

解析规则与前端 utils/wikiLink.js 保持一致（同设计文档约定）。
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
WIKI_LINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+)\]\]")
MD_LINK_RE = re.compile(r"(?<!!)(?<!\])\[[^\]\n]*\]\(([^)\s]+)[^)]*\)")
TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\-/\u4e00-\u9fa5]+)")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# 标签允许的字符中 #标题 锚点不适用，链接目标中不允许空白
_ANCHOR_SPLIT_RE = re.compile(r"[#^]")


@dataclass
class LinkRef:
    dst_raw: str          # 归一化前的目标（已去 #锚点 与扩展名处理前的原始部分）
    dst_alias: str        # 链接原文（含 |别名 部分）
    link_type: str        # wiki / embed / md
    dst_path: Optional[str] = None  # 归一化解析结果；None = 悬空


@dataclass
class ParsedDoc:
    title: str = ""
    tags: List[str] = field(default_factory=list)
    links: List[LinkRef] = field(default_factory=list)
    body_text: str = ""   # 去 Markdown 语义的纯文本（搜索索引用）


def split_frontmatter(content: str) -> Tuple[Dict[str, object], str]:
    """极简 YAML frontmatter 解析：只支持 title/tags/aliases/created 等顶层标量与简单列表。
    解析失败返回 ({}, 原文)，不阻断保存。"""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    raw = m.group(1)
    data: Dict[str, object] = {}
    current_key: Optional[str] = None
    try:
        for line in raw.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if line.startswith("  - ") and current_key:
                data.setdefault(current_key, [])
                if isinstance(data[current_key], list):
                    data[current_key].append(line[4:].strip().strip("'\""))
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = None
            if not value:
                current_key = key
                continue
            if value.startswith("[") and value.endswith("]"):
                items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                data[key] = [v for v in items if v]
            else:
                data[key] = value.strip("'\"")
    except Exception:
        return {}, content
    return data, content[m.end():]


def _strip_code(text: str) -> str:
    """移除围栏代码块与行内代码（其中的 #tag / [[link]] 不提取）。"""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    return text


def extract_title(content: str, fallback_name: str) -> str:
    fm, body = split_frontmatter(content)
    title = fm.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    m = H1_RE.search(body)
    if m:
        return re.sub(r"[`*_]", "", m.group(1)).strip()
    return fallback_name


def extract_tags(content: str) -> List[str]:
    fm, body = split_frontmatter(content)
    tags: List[str] = []
    fm_tags = fm.get("tags")
    if isinstance(fm_tags, list):
        tags.extend(str(t) for t in fm_tags)
    elif isinstance(fm_tags, str):
        tags.extend(t for t in re.split(r"[,\s]+", fm_tags) if t)
    for t in TAG_RE.findall(_strip_code(body)):
        tag = t.rstrip("/")
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def parse_links(content: str) -> List[LinkRef]:
    """提取双链 / 嵌入 / 标准相对 .md 链接（代码块内忽略）。"""
    fm, body = split_frontmatter(content)
    visible = _strip_code(body)
    links: List[LinkRef] = []
    for m in WIKI_LINK_RE.finditer(visible):
        bang, inner = m.group(1), m.group(2).strip()
        if not inner or inner.startswith("#"):  # 纯锚点/纯标签链接（[[#标题]]）不入索引
            continue
        links.append(LinkRef(dst_raw=inner, dst_alias=inner, link_type="embed" if bang else "wiki"))
    for m in MD_LINK_RE.finditer(visible):
        target = m.group(1).strip()
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
            continue  # 外链忽略
        if target.endswith(".md") or ".md#" in target:
            dst = target.split("#", 1)[0].split("?", 1)[0]
            if dst.endswith(".md"):
                links.append(LinkRef(dst_raw=dst, dst_alias=dst, link_type="md"))
    return links


def resolve_link(dst_raw: str, src_path: str, path_set: Set[str]) -> Optional[str]:
    """目标解析（同 Obsidian）：

    1. 去扩展名后按「去锚点目标」在 Vault 内精确匹配；
    2. 相对当前文档目录匹配；
    3. 任意目录下同名（去扩展名）匹配。
    仍失败返回 None（悬空链接）。
    """
    target = _ANCHOR_SPLIT_RE.split(dst_raw, maxsplit=1)[0].strip()
    target = target.split("|", 1)[0].strip()  # [[目标|别名]] 取目标部分
    if not target:
        return None
    if target.endswith(".md"):
        target = target[: -len(".md")]

    def _hit(no_ext: str) -> Optional[str]:
        if no_ext + ".md" in path_set:
            return no_ext + ".md"
        return None

    hit = _hit(target)
    if hit:
        return hit
    # 相对当前文档目录
    folder = src_path.rsplit("/", 1)[0] if "/" in src_path else ""
    if folder:
        hit = _hit(f"{folder}/{target}")
        if hit:
            return hit
    # 任意目录同名
    name = target.rsplit("/", 1)[-1]
    for p in path_set:
        if p.endswith("/" + name + ".md") or p == name + ".md":
            return p
    return None


def to_plain_text(content: str) -> str:
    """去 Markdown 语义，保留可读文本（搜索索引用）。"""
    _, body = split_frontmatter(content)
    text = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.DOTALL)
    text = re.sub(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_~>`]{1,3}", "", text)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"^-{3,}\s*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_doc(content: str, fallback_title: str, src_path: str, path_set: Set[str]) -> ParsedDoc:
    doc = ParsedDoc(
        title=extract_title(content, fallback_title),
        tags=extract_tags(content),
    )
    for ref in parse_links(content):
        ref.dst_path = resolve_link(ref.dst_raw, src_path, path_set)
        doc.links.append(ref)
    doc.body_text = to_plain_text(content)
    return doc
