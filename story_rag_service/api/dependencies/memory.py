"""记忆查询相关依赖提供器。"""

from __future__ import annotations

from dataclasses import dataclass

from application.story_memory import StoryMemoryService
from bootstrap.container import get_container
from services.session_manager import SessionManager
from services.summary_memory_manager import SummaryMemoryManager


@dataclass(frozen=True)
class StoryMemoryDependencies:
    """记忆查询路由所需的最小依赖集合。"""

    session_manager: SessionManager
    summary_memory_manager: SummaryMemoryManager
    story_memory_service: StoryMemoryService


def get_story_memory_dependencies() -> StoryMemoryDependencies:
    """返回记忆查询路由使用的细粒度依赖。"""
    services = get_container()
    return StoryMemoryDependencies(
        session_manager=services.session_manager,
        summary_memory_manager=services.summary_memory_manager,
        story_memory_service=services.story_memory_service,
    )
