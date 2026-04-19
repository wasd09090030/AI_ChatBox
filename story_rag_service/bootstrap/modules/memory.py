"""记忆与运行态相关服务装配。"""

from __future__ import annotations

from dataclasses import dataclass

from application.story_memory import StoryMemoryService
from repositories.entity_state_event_repository import SqliteEntityStateEventRepository
from repositories.entity_state_repository import SqliteEntityStateRepository
from repositories.story_runtime_repository import SqliteStoryRuntimeRepository
from services.entity_patch_update_service import EntityPatchUpdateService
from services.entity_state_event_replay_service import EntityStateEventReplayService
from services.entity_state_fallback_service import EntityStateFallbackService
from services.entity_state_manager import EntityStateManager
from services.entity_state_projection_service import EntityStateProjectionService
from services.roleplay_profile_manager import RoleplayProfileManager
from services.story_generation.entity_patch_applier import EntityPatchApplier
from services.story_generation.entity_patch_extractor import EntityPatchExtractor
from services.story_generation.entity_patch_validator import EntityPatchValidator
from services.story_runtime_manager import StoryRuntimeManager
from services.summary_memory_manager import SummaryMemoryManager


@dataclass(frozen=True)
class MemoryModuleServices:
    """记忆与运行态相关服务集合。"""

    roleplay_manager: RoleplayProfileManager
    summary_memory_manager: SummaryMemoryManager
    entity_state_repository: SqliteEntityStateRepository
    entity_state_event_repository: SqliteEntityStateEventRepository
    entity_state_projection_service: EntityStateProjectionService
    entity_state_event_replay_service: EntityStateEventReplayService
    entity_patch_extractor: EntityPatchExtractor
    entity_patch_validator: EntityPatchValidator
    entity_patch_applier: EntityPatchApplier
    entity_state_manager: EntityStateManager
    entity_state_fallback_service: EntityStateFallbackService
    entity_patch_update_service: EntityPatchUpdateService
    story_runtime_manager: StoryRuntimeManager
    story_memory_service: StoryMemoryService


def build_memory_module(
    *,
    database_path: str,
    lorebook_manager,
    session_manager,
    script_design_app,
    story_manager,
) -> MemoryModuleServices:
    """装配摘要记忆、实体状态与运行态相关服务。"""
    roleplay_manager = RoleplayProfileManager()
    summary_memory_manager = SummaryMemoryManager(db_path=database_path)
    entity_state_repository = SqliteEntityStateRepository(database_path)
    entity_state_event_repository = SqliteEntityStateEventRepository(database_path)
    entity_state_projection_service = EntityStateProjectionService()
    entity_state_event_replay_service = EntityStateEventReplayService(
        entity_state_repository=entity_state_repository,
        entity_state_event_repository=entity_state_event_repository,
        entity_state_projection_service=entity_state_projection_service,
    )
    entity_patch_extractor = EntityPatchExtractor()
    entity_patch_validator = EntityPatchValidator()
    entity_patch_applier = EntityPatchApplier(entity_state_projection_service)
    entity_state_manager = EntityStateManager(
        repository=entity_state_repository,
        lorebook_manager=lorebook_manager,
    )
    entity_state_fallback_service = EntityStateFallbackService(
        entity_state_manager=entity_state_manager,
        entity_state_event_replay_service=entity_state_event_replay_service,
    )
    entity_patch_update_service = EntityPatchUpdateService(
        lorebook_manager=lorebook_manager,
        entity_state_manager=entity_state_manager,
        entity_state_fallback_service=entity_state_fallback_service,
        entity_state_event_repository=entity_state_event_repository,
        entity_patch_extractor=entity_patch_extractor,
        entity_patch_validator=entity_patch_validator,
        entity_patch_applier=entity_patch_applier,
    )
    story_runtime_repository = SqliteStoryRuntimeRepository(database_path)
    story_runtime_manager = StoryRuntimeManager(
        repository=story_runtime_repository,
        script_design_app=script_design_app,
        story_manager=story_manager,
    )
    story_memory_service = StoryMemoryService(
        session_manager=session_manager,
        summary_memory_manager=summary_memory_manager,
        story_runtime_manager=story_runtime_manager,
        entity_state_event_replay_service=entity_state_event_replay_service,
    )

    return MemoryModuleServices(
        roleplay_manager=roleplay_manager,
        summary_memory_manager=summary_memory_manager,
        entity_state_repository=entity_state_repository,
        entity_state_event_repository=entity_state_event_repository,
        entity_state_projection_service=entity_state_projection_service,
        entity_state_event_replay_service=entity_state_event_replay_service,
        entity_patch_extractor=entity_patch_extractor,
        entity_patch_validator=entity_patch_validator,
        entity_patch_applier=entity_patch_applier,
        entity_state_manager=entity_state_manager,
        entity_state_fallback_service=entity_state_fallback_service,
        entity_patch_update_service=entity_patch_update_service,
        story_runtime_manager=story_runtime_manager,
        story_memory_service=story_memory_service,
    )
