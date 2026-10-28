"""Wiki 附件：作为普通文件进 Git 工作区 attachments/ 目录，随文档一起提交。"""

import re
from pathlib import Path

from app.core.exceptions import bad_request, not_found
from app.models.wiki.wiki_vault import WikiVault
from app.services.wiki.path_security import validate_rel_path
from app.services.wiki.vault_service import vault_dir

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 单文件 20MB，沿用资源平台策略

ATTACHMENT_PREFIX = "attachments/"

# 常见媒体类型（按扩展名）；未知类型按 application/octet-stream 返回
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}

_SAFE_NAME_RE = re.compile(r"[^\w\-.一-鿿]+", re.UNICODE)


def _sanitize_filename(filename: str) -> str:
    """取文件名本体（去路径），替换危险字符，拒绝空名。"""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = _SAFE_NAME_RE.sub("_", name).strip("._ ")
    if not name:
        raise bad_request("wiki_attachment_invalid", "文件名非法")
    return name


def _attachment_dir(vault: WikiVault) -> Path:
    d = vault_dir(vault) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def save_attachment(vault: WikiVault, filename: str, data: bytes) -> dict:
    """保存附件到工作区 attachments/ 目录，重名自动加 -2/-3 后缀。不入索引、不提交。"""
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise bad_request(
            "wiki_attachment_too_large",
            f"附件超过 {MAX_ATTACHMENT_SIZE // 1024 // 1024}MB 上限",
        )
    name = _sanitize_filename(filename)
    target_dir = _attachment_dir(vault)

    target = target_dir / name
    stem, suffix = target.stem, target.suffix
    for i in range(2, 1000):
        if not target.exists():
            break
        target = target_dir / f"{stem}-{i}{suffix}"
    if target.exists():
        raise bad_request("wiki_attachment_exists", "同名附件过多，请重命名后重试")

    target.write_bytes(data)
    rel = f"{ATTACHMENT_PREFIX}{target.name}"
    return {"path": rel, "name": target.name, "size": len(data)}


async def read_attachment(vault: WikiVault, path: str) -> tuple[bytes, str]:
    """读取附件字节与媒体类型。仅允许 attachments/ 内的文件。"""
    normalized = validate_rel_path(path, expect_md=False)
    if not normalized.startswith(ATTACHMENT_PREFIX) or normalized == ATTACHMENT_PREFIX:
        raise bad_request("wiki_attachment_invalid", "附件路径必须在 attachments/ 目录内")

    root = vault_dir(vault).resolve()
    target = (root / normalized).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise not_found("wiki_attachment_not_found", f"附件不存在: {path}")

    media_type = _MEDIA_TYPES.get(target.suffix.lower(), "application/octet-stream")
    return target.read_bytes(), media_type
