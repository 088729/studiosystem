"""存储后端公共接口与工具。"""
import re
import uuid
from pathlib import Path

# 文件名白名单：字母数字、下划线、点、连字符
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(filename: str) -> str:
    """清洗文件名：去路径成分、白名单字符、限制长度，空名用 uuid 兜底。

    约定：清洗必须保持「无路径成分且带扩展名」，调用方以 {path}/{filename}
    拼出存储相对路径（导图资产的 relative_path 依赖这一稳定性）。
    """
    name = _SAFE_NAME.sub("-", Path(filename or "").name).strip("-.") or uuid.uuid4().hex
    if len(name) > 120:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:100] + ("." + ext if dot else "")) if dot else name[:120]
    return name
