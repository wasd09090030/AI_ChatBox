"""路由与图执行共享的服务上下文。

兼容桥接层：真实装配逻辑已迁移到 `bootstrap.container`。
"""

from bootstrap.container import (
    ServiceContainer,
    get_container,
    get_services,
    init_services,
    reset_container,
    set_container,
)


def __getattr__(name: str):
    """兼容桥接：支持历史代码通过 ctx.<service> 访问服务。"""
    if name in {
        "vector_store",
        "lorebook_manager",
        "history_manager",
        "session_manager",
        "story_generator",
        "story_adjustment_service",
        "world_manager",
        "world_app",
        "story_manager",
        "story_consistency_rebuild_service",
        "script_design_app",
        "roleplay_manager",
        "summary_memory_manager",
        "story_runtime_manager",
        "entity_state_manager",
        "entity_state_fallback_service",
        "entity_state_event_repository",
        "entity_state_projection_service",
        "entity_state_event_replay_service",
        "entity_patch_extractor",
        "entity_patch_validator",
        "entity_patch_applier",
        "entity_patch_update_service",
        "story_memory_service",
        "user_manager_ref",
    }:
        container = get_container()
        return getattr(container, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ServiceContainer",
    "get_container",
    "get_services",
    "set_container",
    "reset_container",
    "init_services",
]
