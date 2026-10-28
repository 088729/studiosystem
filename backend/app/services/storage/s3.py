"""S3 兼容存储后端：一套适配器覆盖 AWS S3、阿里云 OSS、腾讯云 COS、七牛、华为 OBS、MinIO、Cloudflare R2。

依赖 boto3（可选扩展：pip install -e ".[s3]"）。阻塞调用放入线程池，避免卡事件循环。

URL 语义：
- 配置 STORAGE_S3_PUBLIC_BASE（桶的公共访问域名 / CDN 域名，推荐公共读桶）时返回永久直链；
- 未配置时返回 7 天预签名 URL（私有桶可用，但内嵌到评论等长生命周期内容的图片会过期，不推荐）。
"""
import asyncio

try:
    import boto3
except ImportError:  # 未安装 s3 扩展时允许导入本模块（仅在选中 s3 后端时才真正需要）
    boto3 = None

from app.core.config import get_settings
from app.services.storage.base import safe_filename


class S3Storage:
    def __init__(self):
        if boto3 is None:
            raise RuntimeError("缺少 boto3，请先安装：pip install -e \".[s3]\"")
        from botocore.config import Config as BotoConfig

        s = get_settings()
        self.bucket = s.storage_s3_bucket
        self.public_base = (s.storage_s3_public_base or "").rstrip("/")
        self._client = boto3.resource(
            "s3",
            endpoint_url=s.storage_s3_endpoint_url or None,
            aws_access_key_id=s.storage_s3_access_key,
            aws_secret_access_key=s.storage_s3_secret_key,
            region_name=s.storage_s3_region or None,
            config=BotoConfig(s3={"addressing_style": s.storage_s3_addressing or "auto"}),
        )

    async def upload(self, file_bytes: bytes, filename: str, path: str) -> dict:
        key = f"{path}/{safe_filename(filename)}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.Object(self.bucket, key).put(
                Body=file_bytes,
                ContentType=_guess_content_type(key),
            ),
        )
        url = self._url_for(key)
        return {"path": key, "url": url}

    async def delete(self, relative_path: str) -> dict:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._client.Object(self.bucket, relative_path).delete())
        return {"deleted": relative_path, "exists": False}

    def _url_for(self, key: str) -> str:
        if self.public_base:
            return f"{self.public_base}/{key}"
        # 私有桶：7 天预签名（评论等内嵌长周期内容的图片会过期，建议配置公共域名）
        return self._client.meta.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=7 * 24 * 3600,
        )


def _guess_content_type(key: str) -> str:
    import mimetypes

    return mimetypes.guess_type(key)[0] or "application/octet-stream"
