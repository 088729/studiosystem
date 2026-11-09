"""Wiki adapter: local path pre-validation (mirrors backend path_security),
tree rendering, page trimming."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from ..errors import StudioError

MAX_PATH_LENGTH = 512

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_FORBIDDEN_PARTS = {".git", ".obsidian", ".trash"}
_CONTROL_RE = re.compile(r"[\x00-\x1f]")

MAX_PAGE_CHARS = 50000


def validate_rel_path(path: str, *, expect_md: bool = True) -> str:
    """Local pre-validation, same rules as the backend's `validate_rel_path`.

    Raises StudioError(code="wiki_path_invalid") — surfaced to the model as an
    `isError` tool result, not a protocol error.
    """
    if not path or not isinstance(path, str):
        raise StudioError("wiki_path_invalid", "路径不能为空")
    if len(path) > MAX_PATH_LENGTH:
        raise StudioError("wiki_path_invalid", "路径过长")
    if "\\" in path:
        raise StudioError("wiki_path_invalid", "路径不允许包含反斜杠，请使用 / 分隔")
    if _CONTROL_RE.search(path):
        raise StudioError("wiki_path_invalid", "路径不允许包含控制字符")

    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise StudioError("wiki_path_invalid", "不允许绝对路径")

    parts = pure.parts
    if not parts:
        raise StudioError("wiki_path_invalid", "路径不能为空")
    for part in parts:
        if part in ("", ".", ".."):
            raise StudioError("wiki_path_invalid", "路径不允许包含 . 或 ..")
        stem = part[: -len(".md")] if part.lower().endswith(".md") else part
        if part.upper() in _WINDOWS_RESERVED or stem.upper() in _WINDOWS_RESERVED:
            raise StudioError("wiki_path_invalid", f"路径包含系统保留名: {part}")
        if part in _FORBIDDEN_PARTS:
            raise StudioError("wiki_path_invalid", f"路径包含保留目录: {part}")
        if part.endswith(" ") or part.endswith("."):
            raise StudioError("wiki_path_invalid", "路径片段不允许以空格或点结尾")

    normalized = "/".join(parts)
    if expect_md:
        if not normalized.endswith(".md"):
            raise StudioError("wiki_path_invalid", "文档路径必须以 .md 结尾")
        name = parts[-1][: -len(".md")]
        if not name:
            raise StudioError("wiki_path_invalid", "文档文件名不能为空")
    return normalized


def page_title_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name[: -len(".md")] if name.endswith(".md") else name


def render_tree(nodes: list[dict[str, Any]], *, max_lines: int = 500) -> str:
    """Render backend TreeNode list as an indented text tree."""
    lines: list[str] = []

    def walk(node: dict[str, Any], depth: int) -> None:
        if len(lines) >= max_lines:
            return
        icon = "📄" if node.get("type") == "page" else "📁"
        lines.append(f"{'  ' * depth}{icon} {node.get('name', '')}  ({node.get('path')})")
        for child in node.get("children") or []:
            walk(child, depth + 1)

    for n in nodes:
        walk(n, 0)
    if len(lines) >= max_lines:
        lines.append("…（目录树过大已截断）")
    return "\n".join(lines)


def trim_page_content(content: str, *, max_chars: int = MAX_PAGE_CHARS) -> tuple[str, bool]:
    if len(content) <= max_chars:
        return content, False
    head = content[: max_chars // 2]
    tail = content[-max_chars // 2 :]
    return f"{head}\n\n…（中间省略 {len(content) - max_chars} 字符）…\n\n{tail}", True


def status_label(status: str | None) -> str:
    labels = {
        "ready": "就绪",
        "cloning": "克隆中",
        "indexing": "索引中",
        "importing": "导入中",
        "error": "错误",
    }
    return labels.get(status or "", status or "未知")
