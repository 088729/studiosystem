import re
from pathlib import PurePosixPath
from typing import Optional

from app.core.exceptions import bad_request

MAX_PATH_LENGTH = 512

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_FORBIDDEN_PARTS = {".git", ".obsidian", ".trash"}

_CONTROL_RE = re.compile(r"[\x00-\x1f]")


def validate_rel_path(path: str, *, expect_md: bool = True) -> str:
    """校验并归一化仓库内相对路径（POSIX 风格）。非法路径抛 400 wiki_path_invalid。"""
    if not path or not isinstance(path, str):
        raise bad_request("wiki_path_invalid", "路径不能为空")
    if len(path) > MAX_PATH_LENGTH:
        raise bad_request("wiki_path_invalid", "路径过长")
    if "\\" in path:
        raise bad_request("wiki_path_invalid", "路径不允许包含反斜杠，请使用 / 分隔")
    if _CONTROL_RE.search(path):
        raise bad_request("wiki_path_invalid", "路径不允许包含控制字符")

    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise bad_request("wiki_path_invalid", "不允许绝对路径")

    parts = pure.parts
    if not parts:
        raise bad_request("wiki_path_invalid", "路径不能为空")
    for part in parts:
        if part in ("", ".", ".."):
            raise bad_request("wiki_path_invalid", "路径不允许包含 . 或 ..")
        if part.lower() in _WINDOWS_RESERVED:
            raise bad_request("wiki_path_invalid", f"路径包含系统保留名: {part}")
        if part in _FORBIDDEN_PARTS:
            raise bad_request("wiki_path_invalid", f"路径包含保留目录: {part}")
        if part.endswith(" ") or part.endswith("."):
            raise bad_request("wiki_path_invalid", "路径片段不允许以空格或点结尾")

    normalized = "/".join(parts)
    if expect_md:
        if not normalized.endswith(".md"):
            raise bad_request("wiki_path_invalid", "文档路径必须以 .md 结尾")
        name = parts[-1][: -len(".md")]
        if not name:
            raise bad_request("wiki_path_invalid", "文档文件名不能为空")
    return normalized


def folder_of(path: str) -> str:
    """docs/a/b.md -> docs/a；根目录返回 ""。"""
    idx = path.rfind("/")
    return path[:idx] if idx > 0 else ("" if idx < 0 else path[:idx])


def page_title_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name[: -len(".md")] if name.endswith(".md") else name


def to_md_path(no_ext_or_any: str) -> Optional[str]:
    """把「去扩展名目标」转成可能的 .md 相对路径；无扩展名概念时返回 None。"""
    if not no_ext_or_any or no_ext_or_any.endswith("/"):
        return None
    return no_ext_or_any if no_ext_or_any.endswith(".md") else no_ext_or_any + ".md"
