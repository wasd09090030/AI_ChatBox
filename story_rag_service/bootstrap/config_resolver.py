"""组合根配置解析器。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config import settings


@dataclass(frozen=True)
class BootstrapRuntimeConfig:
    """组合根阶段使用的运行时配置切片。"""

    database_path: str
    upload_dir: Path


@dataclass(frozen=True)
class StoryGraphFeatureFlags:
    """Story Graph 运行阶段使用的特性开关切片。"""

    rp_story_state_enabled: bool
    rp_debug_payload_enabled: bool


@dataclass(frozen=True)
class StoryGraphRuntimeConfig:
    """Story Graph 运行阶段使用的运行时配置切片。"""

    checkpoint_backend: str
    checkpoint_sqlite_path: str


def resolve_bootstrap_runtime_config() -> BootstrapRuntimeConfig:
    """从全局 settings 解析组合根需要的最小配置集。"""
    database_path = settings.database_path
    upload_dir = Path(database_path).parent / "FileUpload"
    return BootstrapRuntimeConfig(
        database_path=database_path,
        upload_dir=upload_dir,
    )


def resolve_story_graph_feature_flags() -> StoryGraphFeatureFlags:
    """从全局 settings 解析 Story Graph 使用的最小特性开关集。"""
    return StoryGraphFeatureFlags(
        rp_story_state_enabled=bool(settings.rp_story_state_enabled),
        rp_debug_payload_enabled=bool(settings.rp_debug_payload_enabled),
    )


def resolve_story_graph_runtime_config() -> StoryGraphRuntimeConfig:
    """从全局 settings 解析 Story Graph 使用的最小运行时配置集。"""
    return StoryGraphRuntimeConfig(
        checkpoint_backend=str(settings.langgraph_checkpoint_backend or "memory"),
        checkpoint_sqlite_path=str(settings.langgraph_checkpoint_sqlite_path),
    )
