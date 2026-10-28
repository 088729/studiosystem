import logging
import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Studio System Backend"
    debug: bool = False

    mongodb_uri: str = "mongodb://localhost:27017/studio_system"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 120
    long_token_expire_days: int = 30

    resourceplatform_base_url: str = "http://localhost:9000"
    resourceplatform_token: str = ""

    # 文件存储后端：local（默认，本地磁盘，经 /uploads 静态访问）| s3（S3 兼容云）| resourceplatform（自建文件服务）
    storage_backend: str = "local"
    storage_dir: str = "./data/uploads"  # local 后端的存储根目录，生产指向持久化卷

    # STORAGE_BACKEND=s3 时的 S3 兼容配置（AWS S3 / 阿里云 OSS / 腾讯云 COS / 七牛 / 华为 OBS / MinIO / R2）
    storage_s3_endpoint_url: str = ""  # 如 https://oss-cn-hangzhou.aliyuncs.com；AWS 官方云可留空
    storage_s3_access_key: str = ""
    storage_s3_secret_key: str = ""
    storage_s3_bucket: str = ""
    storage_s3_region: str = ""
    # 寻址风格：auto | path | virtual（阿里云 OSS / 腾讯云 COS 为虚拟主机式）
    storage_s3_addressing: str = "auto"
    # 桶的公共访问域名 / CDN 域名（推荐公共读桶）；留空则返回 7 天预签名 URL
    storage_s3_public_base: str = ""

    wiki_repo_root: str = "./data/wiki"  # 生产通过 WIKI_REPO_ROOT 指向挂载卷
    wiki_git_author_email_suffix: str = "wiki.local"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("secret_key", mode="after")
    @classmethod
    def _warn_default_secret(cls, value: str) -> str:
        if value == "change-me-in-production":
            logger.warning(
                "SECRET_KEY 使用默认值，生产环境请务必通过环境变量 SECRET_KEY 设置强密钥"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
