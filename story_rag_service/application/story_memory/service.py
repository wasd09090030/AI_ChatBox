"""故事记忆读模型服务。

面向 API 读取侧，聚合摘要、运行时、实体状态与记忆时间线，
返回统一 story_memory 快照，供前端“设定/记忆”面板直接消费。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from application.memory.journal import list_memory_update_events
from entity_state_response_serializer import serialize_entity_state_collection_payload

from .builder import build_story_memory_payload


class StoryMemoryService:
    """story_memory 快照聚合入口。"""

    def __init__(
        self,
        *,
        session_manager=None,
        summary_memory_manager=None,
        story_runtime_manager=None,
        entity_state_event_replay_service=None,
    ):
        """注入 story_memory 聚合所需依赖。"""
        self.session_manager = session_manager
        self.summary_memory_manager = summary_memory_manager
        self.story_runtime_manager = story_runtime_manager
        self.entity_state_event_replay_service = entity_state_event_replay_service

    def get_story_memory_snapshot(
        self,
        *,
        session_id: str,
        story_id: Optional[str] = None,
        world_id: Optional[str] = None,
        timeline_page: int = 1,
        timeline_page_size: int = 50,
    ) -> Dict[str, Any]:
        """组装并返回故事记忆快照（含时间线分页）。

        数据来源：
        - summary_memory_manager: semantic 摘要层；
        - story_runtime_manager: runtime 层；
        - entity_state_event_replay_service: entity 层；
        - memory_update_journal: timeline 层。
        """
        resolved_story_id = self._resolve_story_id(session_id=session_id, explicit_story_id=story_id)
        session_metadata = self._load_session_metadata(session_id)
        summary_snapshot = self._load_summary_snapshot(session_id)
        runtime_snapshot = self._load_runtime_snapshot(resolved_story_id)
        resolved_world_id = world_id or (session_metadata or {}).get("world_id") or runtime_snapshot.get("world_id")
        entity_snapshot = self._load_entity_snapshot(
            story_id=resolved_story_id,
            session_id=session_id,
        )
        timeline_result = list_memory_update_events(
            session_id=session_id,
            page=timeline_page,
            page_size=timeline_page_size,
        )
        recent_entity_updates = list((entity_snapshot or {}).get("recent_entity_updates") or [])
        story_memory = build_story_memory_payload(
            session_id=session_id,
            story_id=resolved_story_id,
            world_id=resolved_world_id,
            summary_memory_snapshot=summary_snapshot,
            runtime_state_snapshot=runtime_snapshot,
            entity_state_snapshot=entity_snapshot,
            entity_state_updates=recent_entity_updates,
            world_update=None,
            memory_updates=list(timeline_result.get("items") or []),
        )
        return {
            "session_id": session_id,
            "story_id": resolved_story_id,
            "world_id": resolved_world_id,
            "timeline_total": int(timeline_result.get("total") or 0),
            "timeline_page": int(timeline_result.get("page") or timeline_page),
            "timeline_page_size": int(timeline_result.get("page_size") or timeline_page_size),
            "story_memory": story_memory,
        }

    def _resolve_story_id(
        self,
        *,
        session_id: str,
        explicit_story_id: Optional[str],
    ) -> Optional[str]:
        """解析故事 ID（优先显式值，回退 session 推导）。"""
        if explicit_story_id:
            return str(explicit_story_id)
        if self.story_runtime_manager:
            return self.story_runtime_manager.derive_story_id(session_id)
        return None

    def _load_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """读取会话元数据（如 world_id）。"""
        if not self.session_manager:
            return None
        return self.session_manager.get_session_metadata(session_id)

    def _load_summary_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        """读取摘要记忆快照。"""
        if not self.summary_memory_manager:
            return None
        return self.summary_memory_manager.get_summary(session_id)

    def _load_runtime_snapshot(self, story_id: Optional[str]) -> Dict[str, Any]:
        """读取剧本运行时快照并转为 JSON 结构。"""
        if not story_id or not self.story_runtime_manager:
            return {}
        runtime_state = self.story_runtime_manager.get_runtime_state(story_id)
        if runtime_state is None:
            return {}
        return runtime_state.model_dump(mode="json")

    def _load_entity_snapshot(
        self,
        *,
        story_id: Optional[str],
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """通过事件回放读取实体状态快照。"""
        if not story_id or not self.entity_state_event_replay_service:
            return None
        replay_result = self.entity_state_event_replay_service.replay_story_state(
            story_id=story_id,
            session_id=session_id,
            source="story_memory_snapshot",
            allow_empty_result=True,
            persist=False,
        )
        snapshot = serialize_entity_state_collection_payload(
            story_id=story_id,
            session_id=session_id,
            entity_type="character",
            items=replay_result.items,
        )
        snapshot["recent_entity_updates"] = list(replay_result.memory_updates or [])[-20:]
        return snapshot
