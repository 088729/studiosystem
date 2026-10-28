"""ResourcePlatform 适配器：包装原客户端，供自建 NAS / 既有部署继续使用。

STORAGE_BACKEND=resourceplatform 时启用；文件本体仍在 RP，GET 走 RP 静态地址。
"""
from app.services.resource_platform import ResourcePlatformClient


class ResourcePlatformStorage:
    def __init__(self):
        self.client = ResourcePlatformClient()
        self.base_url = self.client.base_url

    async def upload(self, file_bytes: bytes, filename: str, path: str) -> dict:
        return await self.client.upload(file_bytes, filename, path)

    async def delete(self, relative_path: str) -> dict:
        return await self.client.delete(relative_path)
