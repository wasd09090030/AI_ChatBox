"""提供商配置与连通性接口 schema。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProviderConfigUpdate(BaseModel):
    """更新 provider 的 API Key 或自定义 Base URL。"""

    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class TestConnectionRequest(BaseModel):
    """测试当前用户 provider 连通性。"""

    provider: str
    base_url: Optional[str] = None


class SceneModelPreference(BaseModel):
    """特定运行场景下的 provider/model 偏好。"""

    provider: Optional[str] = None
    model: Optional[str] = None


class SceneModelPreferencesUpdate(BaseModel):
    """更新分场景 provider/model 偏好。"""

    story_generation: SceneModelPreference = Field(default_factory=SceneModelPreference)
    input_enhancement: SceneModelPreference = Field(default_factory=SceneModelPreference)
    story_adjustment: SceneModelPreference = Field(default_factory=SceneModelPreference)


class SceneModelPreferencesResponse(BaseModel):
    """当前分场景偏好及其回退默认值。"""

    story_generation: SceneModelPreference = Field(default_factory=SceneModelPreference)
    input_enhancement: SceneModelPreference = Field(default_factory=SceneModelPreference)
    story_adjustment: SceneModelPreference = Field(default_factory=SceneModelPreference)
    fallback: dict[str, Optional[str]]


class DefaultProviderSelection(BaseModel):
    """全局默认 provider/model 选择。"""

    provider: str
    model: str
