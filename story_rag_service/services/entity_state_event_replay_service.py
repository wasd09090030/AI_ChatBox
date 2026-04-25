"""实体状态事件回放服务。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from application.memory import build_memory_update_event, persist_memory_update_events
from entity_state_response_serializer import (
    build_entity_display_name_map,
    serialize_companion_value,
)
from models.entity_state import EntityStateRebuildResponse, EntityStateSnapshot
from models.entity_state_event import EntityStateEventRecord


class EntityStateEventReplayService:
    """基于实体状态事件流重放当前快照。"""

    def __init__(
        self,
        *,
        entity_state_repository,
        entity_state_event_repository,
        entity_state_projection_service,
    ):
        """注入回放所需依赖（事件仓储、快照仓储、投影服务）。"""
        self.entity_state_repository = entity_state_repository
        self.entity_state_event_repository = entity_state_event_repository
        self.entity_state_projection_service = entity_state_projection_service

    def replay_story_state(
        self,
        *,
        story_id: str,
        session_id: str,
        source: str,
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
        source_turn_lte: Optional[int] = None,
        allow_empty_result: bool = False,
        persist: bool = True,
    ) -> EntityStateRebuildResponse:
        """按故事维度回放事件流并重建实体快照。"""
        events = self.entity_state_event_repository.list_by_story_id(story_id)
        return self._replay(
            story_id=story_id,
            session_id=session_id,
            events=events,
            source=source,
            operation_id=operation_id,
            sequence_start=sequence_start,
            source_turn_lte=source_turn_lte,
            allow_empty_result=allow_empty_result,
            persist=persist,
        )

    def replay_session_state(
        self,
        *,
        story_id: str,
        session_id: str,
        source: str,
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
        source_turn_lte: Optional[int] = None,
        allow_empty_result: bool = False,
        persist: bool = True,
    ) -> EntityStateRebuildResponse:
        """按会话维度回放事件流并重建实体快照。"""
        events = self.entity_state_event_repository.list_by_session_id(session_id)
        return self._replay(
            story_id=story_id,
            session_id=session_id,
            events=events,
            source=source,
            operation_id=operation_id,
            sequence_start=sequence_start,
            source_turn_lte=source_turn_lte,
            allow_empty_result=allow_empty_result,
            persist=persist,
        )

    def _replay(
        self,
        *,
        story_id: str,
        session_id: str,
        events: Sequence[EntityStateEventRecord],
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
        source_turn_lte: Optional[int],
        allow_empty_result: bool,
        persist: bool,
    ) -> EntityStateRebuildResponse:
        """执行通用回放流程并产出重建结果。"""
        filtered_events = self._filter_events(
            events=events,
            story_id=story_id,
            session_id=session_id,
            source_turn_lte=source_turn_lte,
        )

        previous_states = self.entity_state_repository.list_by_story_id(story_id)
        previous_by_id = {state.entity_id: state for state in previous_states}
        warnings: List[str] = []

        if not filtered_events and not allow_empty_result:
            return EntityStateRebuildResponse(
                story_id=story_id,
                session_id=session_id,
                rebuilt=False,
                entity_count=len(previous_states),
                memory_updates=[],
                warnings=["no_replayable_entity_events"],
                items=previous_states,
            )

        projected_states = self.entity_state_projection_service.project_events(
            story_id=story_id,
            session_id=session_id,
            base_states=[],
            events=filtered_events,
        )
        projected_by_id = {state.entity_id: state for state in projected_states}
        display_name_map = build_entity_display_name_map([*previous_states, *projected_states])
        memory_updates = self._build_memory_updates(
            session_id=session_id,
            source=source,
            previous_by_id=previous_by_id,
            projected_states=projected_states,
            projected_by_id=projected_by_id,
            replay_event_count=len(filtered_events),
            display_name_map=display_name_map,
        )

        if persist:
            self.entity_state_repository.replace_story_states(
                story_id=story_id,
                session_id=session_id,
                states=list(projected_states),
            )
            persist_memory_update_events(
                memory_updates,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )

        return EntityStateRebuildResponse(
            story_id=story_id,
            session_id=session_id,
            rebuilt=True,
            entity_count=len(projected_states),
            memory_updates=memory_updates,
            warnings=warnings,
            items=list(projected_states),
        )

    @staticmethod
    def _filter_events(
        *,
        events: Iterable[EntityStateEventRecord],
        story_id: str,
        session_id: str,
        source_turn_lte: Optional[int],
    ) -> List[EntityStateEventRecord]:
        """按故事/会话/状态/轮次过滤可回放事件。"""
        filtered: List[EntityStateEventRecord] = []
        for event in events:
            if event.story_id != story_id or event.session_id != session_id:
                continue
            if event.status != "committed":
                continue
            if source_turn_lte is not None and event.source_turn is not None and int(event.source_turn) > int(source_turn_lte):
                continue
            filtered.append(event)
        return filtered

    def _build_memory_updates(
        self,
        *,
        session_id: str,
        source: str,
        previous_by_id: Dict[str, EntityStateSnapshot],
        projected_states: Sequence[EntityStateSnapshot],
        projected_by_id: Dict[str, EntityStateSnapshot],
        replay_event_count: int,
        display_name_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """根据回放前后差异构建 memory_updates 事件。"""
        memory_updates: List[Dict[str, Any]] = []
        for state in projected_states:
            before_state = previous_by_id.get(state.entity_id)
            action = "rebuilt" if before_state else "created"
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="entity_state",
                    action=action,
                    source=source,
                    source_turn=state.last_source_turn,
                    memory_key=state.entity_id,
                    title=f"实体状态已通过事件回放{'重建' if action == 'rebuilt' else '建立'}: {state.display_name}",
                    reason=f"event_replay:{replay_event_count}",
                    before=self._snapshot_preview(before_state, display_name_map=display_name_map),
                    after=self._snapshot_preview(state, display_name_map=display_name_map),
                )
            )

        removed_entity_ids = sorted(set(previous_by_id.keys()) - set(projected_by_id.keys()))
        for entity_id in removed_entity_ids:
            removed_state = previous_by_id[entity_id]
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="entity_state",
                    action="reset",
                    source=source,
                    source_turn=removed_state.last_source_turn,
                    memory_key=entity_id,
                    title=f"实体状态已通过事件回放重置: {removed_state.display_name}",
                    reason="event_replay:entity_removed",
                    before=self._snapshot_preview(removed_state, display_name_map=display_name_map),
                )
            )
        return memory_updates

    @staticmethod
    def _snapshot_preview(
        state: Optional[EntityStateSnapshot],
        *,
        display_name_map: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """提取快照关键字段，用于更新日志展示。"""
        if state is None:
            return None
        resolved_display_name_map = display_name_map or {state.entity_id: state.display_name}
        return {
            "display_name": state.display_name,
            "current_location": state.current_location,
            "inventory": list(state.inventory)[:6],
            "status_tags": list(state.status_tags)[:6],
            "companions": serialize_companion_value(
                list(state.companions)[:6],
                display_name_map=resolved_display_name_map,
            ),
            "short_goal": state.short_goal,
            "last_source_turn": state.last_source_turn,
        }
