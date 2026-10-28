from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class User(Document):
    username: Indexed(str, unique=True)
    hashed_password: Optional[str] = None
    role_name: str = "viewer"
    extra_permissions: List[str] = Field(default_factory=list)
    denied_permissions: List[str] = Field(default_factory=list)

    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    job_scope: Optional[str] = None
    is_active: bool = True

    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            "role_name",
            "is_active",
        ]


class Role(Document):
    name: Indexed(str, unique=True)
    permissions: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "roles"


class PermissionKeyItem(BaseModel):
    key: str
    app_id: Optional[str] = None
    builtin: bool = True


class SsoPlatformConfig(Document):
    permission_keys: List[PermissionKeyItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "sso_platform_config"
