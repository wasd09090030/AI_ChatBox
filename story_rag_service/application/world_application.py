"""世界应用层用例。

应用层负责跨域编排：
1. 世界持久化；
2. Lorebook/RAG 同步；
3. 故事与 lorebook 级联清理。
"""

from typing import Optional, Dict, Any, List

from models.world import World, WorldCreate, WorldUpdate
from models.lorebook import Character, Location, Event, LorebookEntry
from services.world_manager import WorldManager
from services.lorebook_manager import LorebookManager
from services.story_manager import StoryManager
from application.script_design_application import ScriptDesignApplicationService


class WorldApplicationService:
    """世界域用例编排层。"""

    def __init__(
        self,
        world_manager: WorldManager,
        lorebook_manager: LorebookManager,
        story_manager: StoryManager,
        script_design_app: ScriptDesignApplicationService | None = None,
    ):
        """初始化世界应用服务。

        聚合世界、lorebook、故事与剧本设计等跨域能力，统一处理联动场景。
        """
        self.world_manager = world_manager
        self.lorebook_manager = lorebook_manager
        self.story_manager = story_manager
        self.script_design_app = script_design_app

    def create_world(self, world_data: WorldCreate) -> World:
        """创建世界并同步写入世界设定 RAG 条目。"""
        world = self.world_manager.create_world(world_data)
        self._upsert_world_rag_entry(world)
        return world

    def list_worlds(self) -> List[World]:
        """列出全部世界。"""
        return self.world_manager.list_worlds()

    def get_world(self, world_id: str) -> Optional[World]:
        """按 world_id 获取世界。"""
        return self.world_manager.get_world(world_id)

    def update_world(self, world_id: str, world_data: WorldUpdate) -> Optional[World]:
        """更新世界并刷新对应世界设定 RAG 条目。"""
        world = self.world_manager.update_world(world_id, world_data)
        if world is None:
            return None
        self._upsert_world_rag_entry(world)
        return world

    def delete_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        """删除世界及其关联数据。

        级联范围包含：故事、lorebook 条目、可选剧本设计。
        """
        if not self.world_manager.world_exists(world_id):
            return None

        deleted_story_count = self.story_manager.delete_stories_by_world(world_id)
        deleted_lorebook_count = self.lorebook_manager.delete_entries_by_world(world_id)
        deleted_script_design_count = 0
        if self.script_design_app is not None:
            deleted_script_design_count = self.script_design_app.delete_script_designs_by_world(world_id)

        success = self.world_manager.delete_world(world_id)
        if not success:
            return None

        return {
            "success": True,
            "message": f"World '{world_id}' deleted successfully",
            "deleted_stories": deleted_story_count,
            "deleted_lorebook_entries": deleted_lorebook_count,
            "deleted_script_designs": deleted_script_design_count,
        }

    def create_character_in_world(self, world_id: str, character: Character) -> Optional[Dict[str, Any]]:
        """在指定世界下创建角色条目。"""
        if not self.world_manager.world_exists(world_id):
            return None

        entry_id = self.lorebook_manager.create_character(character, world_id=world_id)
        return {
            "success": True,
            "entry_id": entry_id,
            "world_id": world_id,
            "message": f"Character '{character.name}' created in world '{world_id}'",
        }

    def create_location_in_world(self, world_id: str, location: Location) -> Optional[Dict[str, Any]]:
        """在指定世界下创建地点条目。"""
        if not self.world_manager.world_exists(world_id):
            return None

        entry_id = self.lorebook_manager.create_location(location, world_id=world_id)
        return {
            "success": True,
            "entry_id": entry_id,
            "world_id": world_id,
            "message": f"Location '{location.name}' created in world '{world_id}'",
        }

    def create_event_in_world(self, world_id: str, event: Event) -> Optional[Dict[str, Any]]:
        """在指定世界下创建事件条目。"""
        if not self.world_manager.world_exists(world_id):
            return None

        entry_id = self.lorebook_manager.create_event(event, world_id=world_id)
        return {
            "success": True,
            "entry_id": entry_id,
            "world_id": world_id,
            "message": f"Event '{event.name}' created in world '{world_id}'",
        }

    def get_world_entries(self, world_id: str) -> Optional[Dict[str, Any]]:
        """获取指定世界下的全部 lorebook 条目。"""
        if not self.world_manager.world_exists(world_id):
            return None

        entries = self.lorebook_manager.get_entries_by_world(world_id)
        return {
            "success": True,
            "world_id": world_id,
            "count": len(entries),
            "entries": entries,
        }

    def _upsert_world_rag_entry(self, world: World) -> None:
        """将世界信息投影为统一 lorebook 条目并覆盖写入。"""
        try:
            self.lorebook_manager.delete_entry(f"world_{world.id}")
        except Exception:
            pass

        description_parts = [f"世界名称：{world.name}", f"世界描述：{world.description}"]
        if world.genre:
            description_parts.append(f"世界类型：{world.genre}")
        if world.setting:
            description_parts.append(f"时空设定：{world.setting}")
        if world.rules:
            description_parts.append(f"世界规则：{world.rules}")

        world_entry = LorebookEntry(
            id=f"world_{world.id}",
            world_id=world.id,
            type="world_setting",
            name=f"【世界设定】{world.name}",
            description="\n".join(description_parts),
            keywords=[world.name, world.genre or "", "世界设定", "世界观"],
            metadata={
                "is_world_info": True,
                "genre": world.genre,
                "setting": world.setting,
                "rules": world.rules,
            },
            created_at=world.created_at,
        )
        self.lorebook_manager.create_entry(world_entry)
