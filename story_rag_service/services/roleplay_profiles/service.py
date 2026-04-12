"""
角色扮演档案门面服务。

该类保留原有 RoleplayProfileManager 的公开接口，
内部通过细粒度仓储拆分职责，避免单文件代码堆积。
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from models.roleplay import PersonaProfile, PersonaProfileCreate, PersonaProfileUpdate, StoryState, StoryStateUpdate
from services.roleplay_profiles.db import RoleplaySQLiteStore
from services.roleplay_profiles.personas import PersonaStore
from services.roleplay_profiles.story_states import StoryStateStore


class RoleplayProfileManager:
    """角色扮演资料服务（兼容原管理器接口）。"""

    def __init__(self, db_path: Optional[str] = None):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self._db = RoleplaySQLiteStore(db_path)
        self._personas = PersonaStore(self._db)
        self._story_states = StoryStateStore(self._db)

    # 以下私有方法用于保持旧代码潜在依赖的兼容性
    def _connect(self) -> sqlite3.Connection:
        """功能：处理 connect。"""
        return self._db.connect()

    def _init_tables(self) -> None:
        """功能：处理 init tables。"""
        self._db.init_tables()

    @staticmethod
    def _parse_json(value, fallback):
        """功能：解析 JSON。"""
        return RoleplaySQLiteStore.parse_json(value, fallback)

    # 人设档案 CRUD
    def list_personas(self) -> List[PersonaProfile]:
        """功能：查询并返回人格卡列表。"""
        return self._personas.list()

    def get_persona(self, persona_id: str) -> Optional[PersonaProfile]:
        """功能：获取人格卡。"""
        return self._personas.get(persona_id)

    def create_persona(self, data: PersonaProfileCreate) -> PersonaProfile:
        """功能：创建人格卡。"""
        return self._personas.create(data)

    def update_persona(self, persona_id: str, data: PersonaProfileUpdate) -> Optional[PersonaProfile]:
        """功能：更新人格卡。"""
        return self._personas.update(persona_id, data)

    def delete_persona(self, persona_id: str) -> bool:
        """功能：删除人格卡。"""
        return self._personas.delete(persona_id)

    # 故事状态
    def get_story_state(self, session_id: str) -> Optional[StoryState]:
        """功能：获取故事状态。"""
        return self._story_states.get(session_id)

    def upsert_story_state(self, session_id: str, data: StoryStateUpdate) -> StoryState:
        """功能：新增或更新故事状态。"""
        return self._story_states.upsert(session_id, data)
