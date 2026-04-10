"""路由与图执行共享的服务上下文。"""

from dataclasses import dataclass
from typing import Optional
import logging
from application.world_application import WorldApplicationService
from application.script_design_application import ScriptDesignApplicationService
from application.story_memory import StoryMemoryService

from services.vector_store import VectorStoreManager
from services.lorebook_manager import LorebookManager
from services.story_generator import StoryGenerator
from services.story_adjustment_service import StoryAdjustmentService
from services.story_consistency_rebuild_service import StoryConsistencyRebuildService
from services.entity_patch_update_service import EntityPatchUpdateService
from services.entity_state_fallback_service import EntityStateFallbackService
from services.entity_state_event_replay_service import EntityStateEventReplayService
from services.entity_state_manager import EntityStateManager
from services.entity_state_projection_service import EntityStateProjectionService
from services.story_generation.entity_patch_applier import EntityPatchApplier
from services.story_generation.entity_patch_extractor import EntityPatchExtractor
from services.story_generation.entity_patch_validator import EntityPatchValidator
from services.world_manager import WorldManager
from services.story_manager import StoryManager
from services.conversation_history_manager import ConversationHistoryManager
from services.session_manager import SessionManager
from services.roleplay_profile_manager import RoleplayProfileManager
from services.summary_memory_manager import SummaryMemoryManager
from services.story_runtime_manager import StoryRuntimeManager
from repositories.entity_state_event_repository import SqliteEntityStateEventRepository
from repositories.entity_state_repository import SqliteEntityStateRepository
from repositories.script_design_repository import SqliteScriptDesignRepository
from repositories.story_runtime_repository import SqliteStoryRuntimeRepository
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """应用级服务容器。

    统一暴露 API 路由与图执行所需的核心服务，避免在路由层散落实例化逻辑。
    """

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


def set_container(container: ServiceContainer):
    """绑定外部服务容器（应用启动生命周期使用）。"""
    global _container
    _container = container


def reset_container():
    """重置服务容器（应用关闭或测试场景使用）。"""
    global _container
    _container = None


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


def init_services(user_manager=None):
    """初始化并装配后端服务。

    初始化顺序遵循“基础设施 -> 领域服务 -> 编排服务”，
    最后聚合到 `ServiceContainer` 并绑定到模块级单例。
    """
    # 基础设施与核心管理器
    vector_store = VectorStoreManager()
    lorebook_manager = LorebookManager(vector_store)
    history_manager = ConversationHistoryManager(vector_store)
    session_manager = SessionManager()
    world_manager = WorldManager()
    story_manager = StoryManager()

    # 应用服务（聚合仓储与领域服务）
    script_design_repository = SqliteScriptDesignRepository(settings.database_path)
    script_design_app = ScriptDesignApplicationService(
        script_design_repository=script_design_repository,
        world_manager=world_manager,
        story_manager=story_manager,
    )
    world_app = WorldApplicationService(
        world_manager=world_manager,
        lorebook_manager=lorebook_manager,
        story_manager=story_manager,
        script_design_app=script_design_app,
    )
    roleplay_manager = RoleplayProfileManager()
    summary_memory_manager = SummaryMemoryManager()
    entity_state_repository = SqliteEntityStateRepository(settings.database_path)
    entity_state_event_repository = SqliteEntityStateEventRepository(settings.database_path)
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
    # 运行时状态服务
    story_runtime_repository = SqliteStoryRuntimeRepository(settings.database_path)
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

    # 故事生成与后处理编排服务
    story_generator = StoryGenerator(
        lorebook_manager,
        history_manager,
        user_manager=user_manager,
        world_manager=world_manager,
        roleplay_manager=roleplay_manager,
        script_design_app=script_design_app,
        summary_memory_manager=summary_memory_manager,
        story_runtime_manager=story_runtime_manager,
        entity_state_manager=entity_state_manager,
        entity_state_fallback_service=entity_state_fallback_service,
        entity_patch_update_service=entity_patch_update_service,
        entity_state_event_replay_service=entity_state_event_replay_service,
    )
    story_adjustment_service = StoryAdjustmentService(
        story_manager=story_manager,
        user_manager=user_manager,
    )
    story_consistency_rebuild_service = StoryConsistencyRebuildService(
        session_manager=session_manager,
        summary_memory_manager=summary_memory_manager,
        history_manager=history_manager,
        story_runtime_manager=story_runtime_manager,
        entity_state_manager=entity_state_manager,
        entity_state_fallback_service=entity_state_fallback_service,
        entity_state_event_repository=entity_state_event_repository,
        entity_state_event_replay_service=entity_state_event_replay_service,
    )

    # 容器聚合与注册
    container = ServiceContainer(
        vector_store=vector_store,
        lorebook_manager=lorebook_manager,
        history_manager=history_manager,
        session_manager=session_manager,
        story_generator=story_generator,
        story_adjustment_service=story_adjustment_service,
        world_manager=world_manager,
        world_app=world_app,
        story_manager=story_manager,
        story_consistency_rebuild_service=story_consistency_rebuild_service,
        script_design_app=script_design_app,
        roleplay_manager=roleplay_manager,
        summary_memory_manager=summary_memory_manager,
        story_runtime_manager=story_runtime_manager,
        entity_state_manager=entity_state_manager,
        entity_state_fallback_service=entity_state_fallback_service,
        entity_state_event_repository=entity_state_event_repository,
        entity_state_projection_service=entity_state_projection_service,
        entity_state_event_replay_service=entity_state_event_replay_service,
        entity_patch_extractor=entity_patch_extractor,
        entity_patch_validator=entity_patch_validator,
        entity_patch_applier=entity_patch_applier,
        entity_patch_update_service=entity_patch_update_service,
        story_memory_service=story_memory_service,
        user_manager_ref=user_manager,
    )

    set_container(container)

    logger.info("services initialized with hybrid memory mode, session management, and style enhancements")
    return container
