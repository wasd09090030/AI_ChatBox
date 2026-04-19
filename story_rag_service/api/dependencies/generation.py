"""故事生成相关依赖提供器。"""

from __future__ import annotations

from dataclasses import dataclass

from bootstrap.container import get_container
from infrastructure import AnalyticsServiceAdapter, StoryGenerationMetricsRecorderAdapter
from application.ports import AnalyticsSink, MetricsRecorder
from services.session_manager import SessionManager
from services.story_generator import StoryGenerator


@dataclass(frozen=True)
class StoryGenerationDependencies:
    """故事生成路由所需的最小依赖集合。"""

    session_manager: SessionManager
    story_generator: StoryGenerator
    metrics_recorder: MetricsRecorder
    analytics_sink: AnalyticsSink


def get_story_generation_dependencies() -> StoryGenerationDependencies:
    """返回故事生成路由使用的细粒度依赖。"""
    services = get_container()
    return StoryGenerationDependencies(
        session_manager=services.session_manager,
        story_generator=services.story_generator,
        metrics_recorder=StoryGenerationMetricsRecorderAdapter(),
        analytics_sink=AnalyticsServiceAdapter(),
    )
