"""实体状态事件流到当前快照的投影服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Sequence

from models.entity_state import EntityStateSnapshot
from models.entity_state_event import EntityStateEventRecord, EntityStatePatch


class EntityStateProjectionService:
    """将 patch / 事件应用到当前实体快照。"""

    _LIST_FIELDS = {"inventory", "status_tags", "companions"}
    _SCALAR_FIELDS = {"current_location", "short_goal", "state_summary"}

    def apply_patches(
        self,
        *,
        story_id: str,
        session_id: str,
        current_states: Sequence[EntityStateSnapshot],
        patches: Sequence[EntityStatePatch],
    ) -> List[EntityStateSnapshot]:
        """将 patch 集合应用到当前快照集合。"""
        state_map = {item.entity_id: item.model_copy(deep=True) for item in current_states}
        for patch in patches:
            snapshot = state_map.get(patch.entity_id)
            if snapshot is None:
                snapshot = EntityStateSnapshot(
                    story_id=story_id,
                    session_id=session_id,
                    entity_id=patch.entity_id,
                    entity_type=patch.entity_type,
                    display_name=patch.entity_name or patch.entity_id,
                )
                state_map[patch.entity_id] = snapshot
            self._apply_patch(snapshot, patch)
        return sorted(state_map.values(), key=lambda item: item.display_name)

    def project_events(
        self,
        *,
        story_id: str,
        session_id: str,
        base_states: Sequence[EntityStateSnapshot],
        events: Iterable[EntityStateEventRecord],
    ) -> List[EntityStateSnapshot]:
        """根据事件流投影生成当前快照。"""
        state_map = {item.entity_id: item.model_copy(deep=True) for item in base_states}
        for event in events:
            snapshot = state_map.get(event.entity_id)
            if snapshot is None:
                snapshot = EntityStateSnapshot(
                    story_id=story_id,
                    session_id=session_id,
                    entity_id=event.entity_id,
                    entity_type=event.entity_type,
                    display_name=event.entity_name or event.entity_id,
                )
                state_map[event.entity_id] = snapshot
            self._apply_event(snapshot, event)
        return sorted(state_map.values(), key=lambda item: item.display_name)

    def _apply_patch(self, snapshot: EntityStateSnapshot, patch: EntityStatePatch) -> None:
        self._mutate_field(snapshot, patch.field_name, patch.op, patch.value)
        snapshot.last_source_turn = patch.source_turn
        snapshot.updated_at = datetime.now()
        if patch.evidence_text:
            self._append_unique(snapshot.evidence, patch.evidence_text, limit=6)
        if patch.entity_name and snapshot.display_name == snapshot.entity_id:
            snapshot.display_name = patch.entity_name

    def _apply_event(self, snapshot: EntityStateSnapshot, event: EntityStateEventRecord) -> None:
        self._mutate_field(snapshot, event.field_name, event.op, event.value)
        snapshot.last_source_turn = event.source_turn
        snapshot.updated_at = self._normalize_datetime(event.committed_at)
        if event.evidence_text:
            self._append_unique(snapshot.evidence, event.evidence_text, limit=6)
        if event.entity_name and snapshot.display_name == snapshot.entity_id:
            snapshot.display_name = event.entity_name

    def _mutate_field(self, snapshot: EntityStateSnapshot, field_name: str, op: str, value: Any) -> None:
        if field_name in self._LIST_FIELDS:
            current = list(getattr(snapshot, field_name) or [])
            normalized_values = self._normalize_list_values(value)
            if op == "set":
                setattr(snapshot, field_name, normalized_values)
            elif op == "add":
                for item in normalized_values:
                    self._append_unique(current, item)
                setattr(snapshot, field_name, current)
            elif op == "remove":
                to_remove = set(normalized_values)
                setattr(snapshot, field_name, [item for item in current if item not in to_remove])
            elif op in {"clear", "reset"}:
                setattr(snapshot, field_name, [])
            return

        if field_name in self._SCALAR_FIELDS:
            if op in {"clear", "reset"}:
                setattr(snapshot, field_name, None)
            else:
                setattr(snapshot, field_name, self._normalize_scalar_value(value))

    @staticmethod
    def _normalize_scalar_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @staticmethod
    def _normalize_list_values(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            raw_values = value
        else:
            raw_values = [value]
        normalized: List[str] = []
        for item in raw_values:
            text = str(item or "").strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @staticmethod
    def _append_unique(items: List[str], value: str, *, limit: int | None = None) -> None:
        text = str(value or "").strip()
        if not text:
            return
        if text not in items:
            items.append(text)
        if limit is not None and len(items) > limit:
            del items[:-limit]

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        text = str(value or "").strip()
        if not text:
            return datetime.now()
        normalized = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now()
