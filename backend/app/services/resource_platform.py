import mimetypes
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import bad_gateway


class ResourcePlatformClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.resourceplatform_base_url.rstrip("/")
        self.token = settings.resourceplatform_token

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Token": self.token},
            timeout=60.0,
        )

    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        path: str,
    ) -> dict:
        async with self._client() as client:
            try:
                response = await client.post(
                    "/api/upload",
                    data={"path": path},
                    files={"file": (filename, file_bytes, mimetypes.guess_type(filename)[0] or "application/octet-stream")},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise bad_gateway(f"resourceplatform 上传失败: {e.response.status_code}")
            except httpx.RequestError as e:
                raise bad_gateway(f"resourceplatform 上传请求失败: {str(e)}")

    async def delete(self, relative_path: str) -> dict:
        async with self._client() as client:
            try:
                response = await client.delete(f"/api/files/{relative_path}")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {"deleted": relative_path, "exists": False}
                raise bad_gateway(f"resourceplatform 删除失败: {e.response.status_code}")
            except httpx.RequestError as e:
                raise bad_gateway(f"resourceplatform 删除请求失败: {str(e)}")


_resource_platform_client: Optional[ResourcePlatformClient] = None


def get_resource_platform_client() -> ResourcePlatformClient:
    global _resource_platform_client
    if _resource_platform_client is None:
        _resource_platform_client = ResourcePlatformClient()
    return _resource_platform_client
