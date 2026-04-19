"""世界、故事、lorebook、script design、roleplay 与 session 相关依赖提供器。"""

from __future__ import annotations

from dataclasses import dataclass

from application.script_design_application import ScriptDesignApplicationService
from application.world_application import WorldApplicationService
from bootstrap.container import get_container
from repositories.entity_state_event_repository import SqliteEntityStateEventRepository
from services.conversation_history_manager import ConversationHistoryManager
from services.entity_state_event_replay_service import EntityStateEventReplayService
from services.entity_state_fallback_service import EntityStateFallbackService
from services.entity_state_manager import EntityStateManager
from services.lorebook_manager import LorebookManager
from services.roleplay_profile_manager import RoleplayProfileManager
from services.session_manager import SessionManager
from services.story_adjustment_service import StoryAdjustmentService
from services.story_consistency_rebuild_service import StoryConsistencyRebuildService
from services.story_manager import StoryManager
from services.story_runtime_manager import StoryRuntimeManager
from services.summary_memory_manager import SummaryMemoryManager
from services.world_manager import WorldManager


@dataclass(frozen=True)
class WorldStoryDependencies:
    """世界与故事管理路由所需依赖。"""

    world_app: WorldApplicationService
    world_manager: WorldManager
    story_manager: StoryManager
    story_runtime_manager: StoryRuntimeManager
    story_consistency_rebuild_service: StoryConsistencyRebuildService
    entity_state_manager: EntityStateManager
    entity_state_event_repository: SqliteEntityStateEventRepository
    entity_state_event_replay_service: EntityStateEventReplayService
    entity_state_fallback_service: EntityStateFallbackService


@dataclass(frozen=True)
class LorebookDependencies:
    """Lorebook 路由所需依赖。"""

    lorebook_manager: LorebookManager
    world_app: WorldApplicationService


@dataclass(frozen=True)
class ScriptDesignDependencies:
    """剧本设计路由所需依赖。"""

    script_design_app: ScriptDesignApplicationService


@dataclass(frozen=True)
class RoleplayDependencies:
    """角色扮演配置路由所需依赖。"""

    roleplay_manager: RoleplayProfileManager


@dataclass(frozen=True)
class StorySessionDependencies:
    """故事会话路由所需依赖。"""

    session_manager: SessionManager
    summary_memory_manager: SummaryMemoryManager
    history_manager: ConversationHistoryManager
    story_runtime_manager: StoryRuntimeManager
    story_consistency_rebuild_service: StoryConsistencyRebuildService
    entity_state_manager: EntityStateManager
    entity_state_fallback_service: EntityStateFallbackService
    entity_state_event_repository: SqliteEntityStateEventRepository
    entity_state_event_replay_service: EntityStateEventReplayService


@dataclass(frozen=True)
class StoryAdjustmentDependencies:
    """故事改写路由所需依赖。"""

    story_adjustment_service: StoryAdjustmentService


def get_world_story_dependencies() -> WorldStoryDependencies:
    """返回世界与故事管理路由使用的细粒度依赖。"""
    services = get_container()
    return WorldStoryDependencies(
        world_app=services.world_app,
        world_manager=services.world_manager,
        story_manager=services.story_manager,
        story_runtime_manager=services.story_runtime_manager,
        story_consistency_rebuild_service=services.story_consistency_rebuild_service,
        entity_state_manager=services.entity_state_manager,
        entity_state_event_repository=services.entity_state_event_repository,
        entity_state_event_replay_service=services.entity_state_event_replay_service,
        entity_state_fallback_service=services.entity_state_fallback_service,
    )


def get_lorebook_dependencies() -> LorebookDependencies:
    """返回 lorebook 路由使用的细粒度依赖。"""
    services = get_container()
    return LorebookDependencies(
        lorebook_manager=services.lorebook_manager,
        world_app=services.world_app,
    )


def get_script_design_dependencies() -> ScriptDesignDependencies:
    """返回剧本设计路由使用的细粒度依赖。"""
    services = get_container()
    return ScriptDesignDependencies(script_design_app=services.script_design_app)


def get_roleplay_dependencies() -> RoleplayDependencies:
    """返回角色扮演配置路由使用的细粒度依赖。"""
    services = get_container()
    return RoleplayDependencies(roleplay_manager=services.roleplay_manager)


def get_story_session_dependencies() -> StorySessionDependencies:
    """返回故事会话路由使用的细粒度依赖。"""
    services = get_container()
    return StorySessionDependencies(
        session_manager=services.session_manager,
        summary_memory_manager=services.summary_memory_manager,
        history_manager=services.history_manager,
        story_runtime_manager=services.story_runtime_manager,
        story_consistency_rebuild_service=services.story_consistency_rebuild_service,
        entity_state_manager=services.entity_state_manager,
        entity_state_fallback_service=services.entity_state_fallback_service,
        entity_state_event_repository=services.entity_state_event_repository,
        entity_state_event_replay_service=services.entity_state_event_replay_service,
    )


def get_story_adjustment_dependencies() -> StoryAdjustmentDependencies:
    """返回故事改写路由使用的细粒度依赖。"""
    services = get_container()
    return StoryAdjustmentDependencies(
        story_adjustment_service=services.story_adjustment_service,
    )
