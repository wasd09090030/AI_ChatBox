"""世界、故事与基础管理器装配。"""

from __future__ import annotations

from dataclasses import dataclass

from application.script_design_application import ScriptDesignApplicationService
from application.world_application import WorldApplicationService
from repositories.script_design_repository import SqliteScriptDesignRepository
from services.conversation_history_manager import ConversationHistoryManager
from services.lorebook_manager import LorebookManager
from services.session_manager import SessionManager
from services.story_manager import StoryManager
from services.vector_store import VectorStoreManager
from services.world_manager import WorldManager


@dataclass(frozen=True)
class WorldModuleServices:
    """世界域相关的基础设施与应用服务。"""

    vector_store: VectorStoreManager
    lorebook_manager: LorebookManager
    history_manager: ConversationHistoryManager
    session_manager: SessionManager
    world_manager: WorldManager
    story_manager: StoryManager
    script_design_app: ScriptDesignApplicationService
    world_app: WorldApplicationService


def build_world_module(*, database_path: str) -> WorldModuleServices:
    """装配世界、故事、lorebook 相关基础服务。"""
    vector_store = VectorStoreManager()
    lorebook_manager = LorebookManager(vector_store)
    history_manager = ConversationHistoryManager(vector_store)
    session_manager = SessionManager()
    world_manager = WorldManager()
    story_manager = StoryManager()

    script_design_repository = SqliteScriptDesignRepository(database_path)
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

    return WorldModuleServices(
        vector_store=vector_store,
        lorebook_manager=lorebook_manager,
        history_manager=history_manager,
        session_manager=session_manager,
        world_manager=world_manager,
        story_manager=story_manager,
        script_design_app=script_design_app,
        world_app=world_app,
    )
