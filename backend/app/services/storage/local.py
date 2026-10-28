"""本地磁盘存储后端：文件落 STORAGE_DIR，经 /uploads 静态路由公开访问（与 RP 的公开 GET 语义一致）。"""
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import not_found
from app.services.storage.base import safe_filename


class LocalStorage:
    def __init__(self):
        settings = get_settings()
        self.root = Path(settings.storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        """把相对路径解析到存储根目录内，防目录穿越。"""
        target = (self.root / relative_path).resolve()
        if not str(target).startswith(str(self.root)):
            raise not_found("file_not_found", "文件不存在")
        return target

    async def upload(self, file_bytes: bytes, filename: str, path: str) -> dict:
        """落盘到 {STORAGE_DIR}/{path}/{filename}；重名追加短 uuid 前缀防覆盖。"""
        safe = safe_filename(filename)
        directory = self._resolve(path)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / safe
        if target.exists():
            stem, dot, ext = safe.rpartition(".")
            target = directory / (f"{uuid.uuid4().hex[:8]}-{stem}" + (f".{ext}" if dot else ""))
        target.write_bytes(file_bytes)
        relative_path = f"{path}/{target.name}"
        return {"path": relative_path, "url": f"/uploads/{relative_path}"}

    async def delete(self, relative_path: str) -> dict:
        target = self._resolve(relative_path)
        if target.is_file():
            target.unlink()
            return {"deleted": relative_path, "exists": False}
        return {"deleted": relative_path, "exists": False}
