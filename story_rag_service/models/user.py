"""用户与用户设置模型。"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserSettings(BaseModel):
    """用户设置模型。"""
    theme: str = "system"
    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    story_generation_provider: Optional[str] = None
    story_generation_model: Optional[str] = None
    input_enhancement_provider: Optional[str] = None
    input_enhancement_model: Optional[str] = None
    story_adjustment_provider: Optional[str] = None
    story_adjustment_model: Optional[str] = None

    # 接口密钥（存储时加密）
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    custom_api_key: Optional[str] = None

    # 自定义 Base URL（provider 级覆盖；""/None 表示使用默认值）
    openai_base_url: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    qwen_base_url: Optional[str] = None
    gemini_base_url: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    custom_base_url: Optional[str] = None  # custom provider 必填


class User(BaseModel):
    """用户模型。"""
    id: str = Field(..., description="User unique ID")
    username: Optional[str] = None
    email: Optional[str] = None
    settings: UserSettings = Field(default_factory=UserSettings)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSettingsUpdate(BaseModel):
    """用户设置更新请求。"""
    theme: Optional[str] = None
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class APIKeyUpdate(BaseModel):
    """接口密钥更新请求。"""
    provider: str = Field(
        ...,
        description="Provider: openai, anthropic, deepseek, qwen, gemini, custom",
    )
    api_key: str = Field(..., description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL override (optional)")
