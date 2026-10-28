from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    username: str
    role_name: str = "viewer"
    perms: List[str] = Field(default_factory=list)
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    job_scope: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role_name: str = "viewer"
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    job_scope: Optional[str] = None
    is_active: bool = True


class UserPermissionUpdate(BaseModel):
    role_name: str
    extra: List[str] = Field(default_factory=list)
    denied: List[str] = Field(default_factory=list)


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserJobScopeUpdate(BaseModel):
    job_scope: str


class RoleCreateUpdate(BaseModel):
    name: str
    permissions: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class PermissionKeyCreate(BaseModel):
    key: str
    app_id: Optional[str] = None
    builtin: bool = False


class BatchPermissionsApply(BaseModel):
    usernames: List[str]
    role_name: str
    extra: List[str] = Field(default_factory=list)
    denied: List[str] = Field(default_factory=list)
