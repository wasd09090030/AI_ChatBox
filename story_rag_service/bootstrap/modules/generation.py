"""故事生成与后处理服务装配。"""

from __future__ import annotations

from dataclasses import dataclass

from infrastructure import LangChainLLMGateway, UserSettingsServiceAdapter
from services.story_adjustment_service import StoryAdjustmentService
from services.story_consistency_rebuild_service import StoryConsistencyRebuildService
from services.story_generator import StoryGenerator


@dataclass(frozen=True)
class GenerationModuleServices:
    """故事生成与后处理服务集合。"""

    story_generator: StoryGenerator
    story_adjustment_service: StoryAdjustmentService
    story_consistency_rebuild_service: StoryConsistencyRebuildService


def build_generation_module(
    *,
    lorebook_manager,
    history_manager,
    session_manager,
    world_manager,
    story_manager,
    script_design_app,
    user_manager,
    memory_services,
) -> GenerationModuleServices:
    """装配故事生成与后处理相关服务。"""
    user_settings_reader = UserSettingsServiceAdapter(user_manager)
    llm_gateway = LangChainLLMGateway(user_settings_reader=user_settings_reader)
    story_generator = StoryGenerator(
        lorebook_manager,
        history_manager,
        llm_gateway=llm_gateway,
        world_manager=world_manager,
        roleplay_manager=memory_services.roleplay_manager,
        script_design_app=script_design_app,
        summary_memory_manager=memory_services.summary_memory_manager,
        story_runtime_manager=memory_services.story_runtime_manager,
        entity_state_manager=memory_services.entity_state_manager,
        entity_state_fallback_service=memory_services.entity_state_fallback_service,
        entity_patch_update_service=memory_services.entity_patch_update_service,
        entity_state_event_replay_service=memory_services.entity_state_event_replay_service,
    )
    story_adjustment_service = StoryAdjustmentService(
        story_manager=story_manager,
        llm_gateway=llm_gateway,
    )
    story_consistency_rebuild_service = StoryConsistencyRebuildService(
        session_manager=session_manager,
        summary_memory_manager=memory_services.summary_memory_manager,
        history_manager=history_manager,
        story_runtime_manager=memory_services.story_runtime_manager,
        entity_state_manager=memory_services.entity_state_manager,
        entity_state_fallback_service=memory_services.entity_state_fallback_service,
        entity_state_event_repository=memory_services.entity_state_event_repository,
        entity_state_event_replay_service=memory_services.entity_state_event_replay_service,
    )

    return GenerationModuleServices(
        story_generator=story_generator,
        story_adjustment_service=story_adjustment_service,
        story_consistency_rebuild_service=story_consistency_rebuild_service,
    )
