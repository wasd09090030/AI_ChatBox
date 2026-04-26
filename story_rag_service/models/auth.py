"""认证相关请求与响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuthenticatedUserResponse(BaseModel):
    """返回给前端的当前登录用户信息。"""

    user_id: str
    login_identifier: str
    display_name: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class RegisterRequest(BaseModel):
    """注册请求。"""

    login_identifier: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8, max_length=256)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=64)


class LoginRequest(BaseModel):
    """登录请求。"""

    login_identifier: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8, max_length=256)


class AuthSessionResponse(BaseModel):
    """认证成功后的响应。"""

    user: AuthenticatedUserResponse


class LogoutResponse(BaseModel):
    """登出响应。"""

    success: bool = True


class LegacyClaimRequest(BaseModel):
    """认领旧匿名数据请求。"""

    legacy_user_id: str = Field(..., min_length=3, max_length=256)
    claim_unowned_data: bool = False


class LegacyClaimResponse(BaseModel):
    """旧匿名数据认领结果。"""

    success: bool
    migrated_user_settings: bool = False
    migrated_worlds: int = 0
    migrated_stories: int = 0
    migrated_script_designs: int = 0
    migrated_story_sessions: int = 0
    migrated_lorebook_entries: int = 0
    migrated_runtime_states: int = 0
    migrated_memory_events: int = 0
    migrated_entity_events: int = 0
    claimed_unowned_resources: bool = False
    warnings: list[str] = Field(default_factory=list)
