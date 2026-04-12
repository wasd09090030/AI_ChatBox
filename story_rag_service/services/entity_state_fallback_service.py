"""旧实体状态重建的 fallback / repair 服务。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from models.entity_state import EntityStateCollection, EntityStateRebuildResponse
from models.story import Message

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class EntityStateFallbackService:
    """封装旧实体状态重建逻辑，避免主生成链路直接依赖 manager。"""

    def __init__(self, entity_state_manager=None, entity_state_event_replay_service=None):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.entity_state_manager = entity_state_manager
        self.entity_state_event_replay_service = entity_state_event_replay_service

    def get_story_snapshot(
        self,
        *,
        story_id: str,
        session_id: str,
        entity_type: Optional[str] = None,
        source: str = "entity_state_story_snapshot_bridge",
    ) -> EntityStateCollection:
        """功能：获取故事快照。"""
        replay_items = self._try_replay_story_items(
            story_id=story_id,
            session_id=session_id,
            source=source,
        )
        if replay_items is not None:
            filtered_items = self._filter_items_by_type(replay_items, entity_type=entity_type)
            return EntityStateCollection(
                story_id=story_id,
                session_id=session_id,
                entity_type=entity_type,
                items=filtered_items,
                total=len(filtered_items),
            )

        items = self.entity_state_manager.list_story_states(story_id, entity_type=entity_type) if self.entity_state_manager else []
        return EntityStateCollection(
            story_id=story_id,
            session_id=session_id,
            entity_type=entity_type,
            items=items,
            total=len(items),
        )

    def get_session_snapshot(
        self,
        *,
        session_id: str,
        story_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        source: str = "entity_state_session_snapshot_bridge",
    ) -> EntityStateCollection:
        """功能：获取会话快照。"""
        replay_items = self._try_replay_session_items(
            story_id=story_id,
            session_id=session_id,
            source=source,
        )
        if replay_items is not None:
            filtered_items = self._filter_items_by_type(replay_items, entity_type=entity_type)
            return EntityStateCollection(
                story_id=story_id,
                session_id=session_id,
                entity_type=entity_type,
                items=filtered_items,
                total=len(filtered_items),
            )

        items = self.entity_state_manager.list_session_states(session_id, entity_type=entity_type) if self.entity_state_manager else []
        return EntityStateCollection(
            story_id=story_id,
            session_id=session_id,
            entity_type=entity_type,
            items=items,
            total=len(items),
        )

    def rebuild_session_state(
        self,
        *,
        session_id: str,
        story_id: Optional[str],
        world_id: Optional[str],
        messages: Sequence[Message],
        source: str,
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
        activation_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> EntityStateRebuildResponse:
        """功能：处理 rebuild 会话状态。"""
        if self.entity_state_manager is None or not story_id:
            return EntityStateRebuildResponse(
                story_id=story_id,
                session_id=session_id,
                rebuilt=False,
                entity_count=0,
                memory_updates=[],
                warnings=["entity_state_fallback_unavailable"],
                items=[],
            )

        try:
            result = self.entity_state_manager.rebuild_session_state(
                session_id=session_id,
                story_id=story_id,
                world_id=world_id,
                messages=messages,
                persist=True,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )
            if activation_logs is not None:
                activation_logs.append(
                    {
                        "source": "entity_state_fallback",
                        "event": "rebuilt",
                        "story_id": story_id,
                        "entity_count": len(result.items),
                    }
                )
            return result
        except Exception as exc:
            logger.warning(
                "Legacy entity-state fallback rebuild failed for session %s: %s",
                session_id,
                exc,
            )
            if activation_logs is not None:
                activation_logs.append(
                    {
                        "source": "entity_state_fallback",
                        "event": "rebuild_failed",
                        "story_id": story_id,
                        "reason": str(exc),
                    }
                )
            return EntityStateRebuildResponse(
                story_id=story_id,
                session_id=session_id,
                rebuilt=False,
                entity_count=0,
                memory_updates=[],
                warnings=[str(exc)],
                items=[],
            )

    @staticmethod
    def to_snapshot_payload(response: Optional[EntityStateRebuildResponse]) -> Optional[Dict[str, Any]]:
        """功能：处理 to 快照载荷。"""
        if response is None or not response.rebuilt:
            return None
        snapshot = EntityStateCollection(
            story_id=response.story_id,
            session_id=response.session_id,
            entity_type=None,
            items=response.items,
            total=len(response.items),
        )
        return snapshot.model_dump(mode="json")

    def rebuild_story_state(
        self,
        *,
        story,
        session_id: str,
        runtime_state=None,
        source: str,
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
    ) -> EntityStateRebuildResponse:
        """功能：处理 rebuild 故事状态。"""
        if self.entity_state_manager is None:
            return EntityStateRebuildResponse(
                story_id=getattr(story, "id", None),
                session_id=session_id,
                rebuilt=False,
                entity_count=0,
                memory_updates=[],
                warnings=["entity_state_fallback_unavailable"],
                items=[],
            )
        try:
            return self.entity_state_manager.rebuild_story_state(
                story=story,
                session_id=session_id,
                runtime_state=runtime_state,
                persist=True,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )
        except Exception as exc:
            logger.warning(
                "Legacy entity-state fallback rebuild failed for story %s: %s",
                getattr(story, "id", None),
                exc,
            )
            return EntityStateRebuildResponse(
                story_id=getattr(story, "id", None),
                session_id=session_id,
                rebuilt=False,
                entity_count=0,
                memory_updates=[],
                warnings=[str(exc)],
                items=[],
            )

    def _try_replay_story_items(
        self,
        *,
        story_id: str,
        session_id: str,
        source: str,
    ) -> Optional[List[Any]]:
        """功能：处理 try replay 故事 items。"""
        if self.entity_state_event_replay_service is None:
            return None
        result = self.entity_state_event_replay_service.replay_story_state(
            story_id=story_id,
            session_id=session_id,
            source=source,
            allow_empty_result=True,
            persist=False,
        )
        if not result.rebuilt and not result.items:
            return None
        return list(result.items)

    def _try_replay_session_items(
        self,
        *,
        story_id: Optional[str],
        session_id: str,
        source: str,
    ) -> Optional[List[Any]]:
        """功能：处理 try replay 会话 items。"""
        if self.entity_state_event_replay_service is None or not story_id:
            return None
        result = self.entity_state_event_replay_service.replay_session_state(
            story_id=story_id,
            session_id=session_id,
            source=source,
            allow_empty_result=True,
            persist=False,
        )
        if not result.rebuilt and not result.items:
            return None
        return list(result.items)

    @staticmethod
    def _filter_items_by_type(items: Sequence[Any], *, entity_type: Optional[str]) -> List[Any]:
        """功能：处理 filter items by type。"""
        if not entity_type:
            return list(items)
        return [item for item in items if getattr(item, "entity_type", None) == entity_type]
