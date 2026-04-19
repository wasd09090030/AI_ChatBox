"""应用层端口定义。

集中声明 application 层依赖的抽象边界，降低上层流程编排对具体服务/
仓储实现的直接耦合。当前先提供最小 Protocol 骨架，后续逐步替换具体实现。
"""

from .feature_flags import FeatureFlagReader
from .llm_gateway import LLMGateway
from .observability import AnalyticsSink, MetricsRecorder
from .repositories import (
    EntityStateEventRepositoryPort,
    LorebookRepositoryPort,
    ScriptDesignRepositoryPort,
    StoryRepositoryPort,
    StorySessionRepositoryPort,
)
from .session_context import SessionContextStore
from .story_generation import StoryGenerationExecutor
from .user_settings import UserSettingsReader

__all__ = [
    "AnalyticsSink",
    "EntityStateEventRepositoryPort",
    "FeatureFlagReader",
    "LLMGateway",
    "LorebookRepositoryPort",
    "MetricsRecorder",
    "ScriptDesignRepositoryPort",
    "SessionContextStore",
    "StoryRepositoryPort",
    "StoryGenerationExecutor",
    "StorySessionRepositoryPort",
    "UserSettingsReader",
]
