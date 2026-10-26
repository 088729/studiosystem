from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel


class WikiLink(Document):
    """双链关系。保存文档时由 link_parser 全量替换该 src_path 的记录。"""

    vault_id: Indexed(str)
    src_path: str
    dst_path: Optional[str] = None  # 归一化目标路径；悬空链接为 None
    dst_alias: str = ""  # 链接原文（如 [[笔记|别名]] 的 笔记|别名）
    link_type: str = "wiki"  # wiki([[]]) / embed(![[]]) / md([](x.md))
    is_resolved: bool = False

    class Settings:
        name = "wiki_links"
        indexes = [
            IndexModel([("vault_id", 1), ("src_path", 1)]),
            IndexModel([("vault_id", 1), ("dst_path", 1)]),
            IndexModel([("vault_id", 1), ("is_resolved", 1)]),
        ]
