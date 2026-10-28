"""可插拔文件存储：本地磁盘（默认，开源零依赖）、S3 兼容云、ResourcePlatform 适配器。

统一接口与原 ResourcePlatformClient 保持一致：
- upload(file_bytes, filename, path) -> {"path": 相对路径, "url": 访问 URL}
- delete(relative_path) -> dict

通过 STORAGE_BACKEND 环境变量选择：
- local（默认）：本地磁盘，/uploads 静态访问
- s3：S3 兼容对象存储（AWS S3 / 阿里云 OSS / 腾讯云 COS / 七牛 / 华为 OBS / MinIO / R2）
- resourceplatform：自建 ResourcePlatform 文件服务
"""
from typing import Optional

from app.core.config import get_settings
from app.services.storage.local import LocalStorage
from app.services.storage.resource_platform import ResourcePlatformStorage

_storage: Optional[object] = None


def get_storage():
    """按配置返回存储后端单例。"""
    global _storage
    if _storage is None:
        backend = (get_settings().storage_backend or "local").lower()
        if backend == "resourceplatform":
            _storage = ResourcePlatformStorage()
        elif backend == "s3":
            from app.services.storage.s3 import S3Storage

            _storage = S3Storage()
        else:
            _storage = LocalStorage()
    return _storage


def reset_storage():
    """重置单例（测试用）。"""
    global _storage
    _storage = None
