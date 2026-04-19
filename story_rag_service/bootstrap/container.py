"""应用容器与服务装配入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import logging

from application.script_design_application import ScriptDesignApplicationService
from application.story_memory import StoryMemoryService
from application.world_application import WorldApplicationService
from bootstrap.config_resolver import resolve_bootstrap_runtime_config
from bootstrap.modules.generation import build_generation_module
from bootstrap.modules.memory import build_memory_module
from bootstrap.modules.world import build_world_module
from repositories.entity_state_event_repository import SqliteEntityStateEventRepository
from services.conversation_history_manager import ConversationHistoryManager
from services.entity_patch_update_service import EntityPatchUpdateService
from services.entity_state_event_replay_service import EntityStateEventReplayService
from services.entity_state_fallback_service import EntityStateFallbackService
from services.entity_state_manager import EntityStateManager
from services.entity_state_projection_service import EntityStateProjectionService
from services.lorebook_manager import LorebookManager
from services.roleplay_profile_manager import RoleplayProfileManager
from services.session_manager import SessionManager
from services.story_adjustment_service import StoryAdjustmentService
from services.story_consistency_rebuild_service import StoryConsistencyRebuildService
from services.story_generation.entity_patch_applier import EntityPatchApplier
from services.story_generation.entity_patch_extractor import EntityPatchExtractor
from services.story_generation.entity_patch_validator import EntityPatchValidator
from services.story_generator import StoryGenerator
from services.story_manager import StoryManager
from services.story_runtime_manager import StoryRuntimeManager
from services.summary_memory_manager import SummaryMemoryManager
from services.vector_store import VectorStoreManager
from services.world_manager import WorldManager

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """应用级服务容器。"""

    vector_store: VectorStoreManager
    lorebook_manager: LorebookManager
    history_manager: ConversationHistoryManager
    session_manager: SessionManager
    story_generator: StoryGenerator
    story_adjustment_service: StoryAdjustmentService
    world_manager: WorldManager
    world_app: WorldApplicationService
    story_manager: StoryManager
    story_consistency_rebuild_service: StoryConsistencyRebuildService
    script_design_app: ScriptDesignApplicationService
    roleplay_manager: RoleplayProfileManager
    summary_memory_manager: SummaryMemoryManager
    story_runtime_manager: StoryRuntimeManager
    entity_state_manager: EntityStateManager
    entity_state_fallback_service: EntityStateFallbackService
    entity_state_event_repository: SqliteEntityStateEventRepository
    entity_state_projection_service: EntityStateProjectionService
    entity_state_event_replay_service: EntityStateEventReplayService
    entity_patch_extractor: EntityPatchExtractor
    entity_patch_validator: EntityPatchValidator
    entity_patch_applier: EntityPatchApplier
    entity_patch_update_service: EntityPatchUpdateService
    story_memory_service: StoryMemoryService
    user_manager_ref: Optional[object] = None


_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """获取已初始化的服务容器。"""
    if _container is None:
        raise RuntimeError("Service container is not initialized. Call init_services() first.")
    return _container


def get_services() -> ServiceContainer:
    """依赖注入别名：返回服务容器。"""
    return get_container()


def set_container(container: ServiceContainer) -> None:
    """绑定外部服务容器。"""
    global _container
    _container = container


def reset_container() -> None:
    """重置服务容器。"""
    global _container
    _container = None


def init_services(user_manager=None) -> ServiceContainer:
    """初始化并装配后端服务。"""
    runtime_config = resolve_bootstrap_runtime_config()
    world_services = build_world_module(database_path=runtime_config.database_path)
    memory_services = build_memory_module(
        database_path=runtime_config.database_path,
        lorebook_manager=world_services.lorebook_manager,
        session_manager=world_services.session_manager,
        script_design_app=world_services.script_design_app,
        story_manager=world_services.story_manager,
    )
    generation_services = build_generation_module(
        lorebook_manager=world_services.lorebook_manager,
        history_manager=world_services.history_manager,
        session_manager=world_services.session_manager,
        world_manager=world_services.world_manager,
        story_manager=world_services.story_manager,
        script_design_app=world_services.script_design_app,
        user_manager=user_manager,
        memory_services=memory_services,
    )

    container = ServiceContainer(
        vector_store=world_services.vector_store,
        lorebook_manager=world_services.lorebook_manager,
        history_manager=world_services.history_manager,
        session_manager=world_services.session_manager,
        story_generator=generation_services.story_generator,
        story_adjustment_service=generation_services.story_adjustment_service,
        world_manager=world_services.world_manager,
        world_app=world_services.world_app,
        story_manager=world_services.story_manager,
        story_consistency_rebuild_service=generation_services.story_consistency_rebuild_service,
        script_design_app=world_services.script_design_app,
        roleplay_manager=memory_services.roleplay_manager,
        summary_memory_manager=memory_services.summary_memory_manager,
        story_runtime_manager=memory_services.story_runtime_manager,
        entity_state_manager=memory_services.entity_state_manager,
        entity_state_fallback_service=memory_services.entity_state_fallback_service,
        entity_state_event_repository=memory_services.entity_state_event_repository,
        entity_state_projection_service=memory_services.entity_state_projection_service,
        entity_state_event_replay_service=memory_services.entity_state_event_replay_service,
        entity_patch_extractor=memory_services.entity_patch_extractor,
        entity_patch_validator=memory_services.entity_patch_validator,
        entity_patch_applier=memory_services.entity_patch_applier,
        entity_patch_update_service=memory_services.entity_patch_update_service,
        story_memory_service=memory_services.story_memory_service,
        user_manager_ref=user_manager,
    )
    set_container(container)
    logger.info("services initialized via bootstrap container modules")
    return container
