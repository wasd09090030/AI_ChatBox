"""实体 patch 应用服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from models.entity_state import EntityStateSnapshot
from models.entity_state_event import (
    EntityPatchApplyResult,
    EntityStateEventRecord,
    EntityStatePatch,
)
from services.entity_state_projection_service import EntityStateProjectionService


class EntityPatchApplier:
    """负责把 patch 转为事件并物化到当前快照。"""

    def __init__(self, projection_service: EntityStateProjectionService):
        self.projection_service = projection_service

    def apply(
        self,
        *,
        story_id: str,
        session_id: str,
        current_states: Sequence[EntityStateSnapshot],
        patches: Sequence[EntityStatePatch],
        source: str,
        operation_id: str | None = None,
        sequence_start: int = 1,
    ) -> EntityPatchApplyResult:
        updated_states = self.projection_service.apply_patches(
            story_id=story_id,
            session_id=session_id,
            current_states=current_states,
            patches=patches,
        )

        current_by_id = {item.entity_id: item for item in current_states}
        updated_by_id = {item.entity_id: item for item in updated_states}
        events: list[EntityStateEventRecord] = []

        next_sequence = max(1, int(sequence_start))
        for patch in patches:
            before_snapshot = current_by_id.get(patch.entity_id)
            after_snapshot = updated_by_id.get(patch.entity_id)
            before_value = getattr(before_snapshot, patch.field_name, None) if before_snapshot else None
            after_value = getattr(after_snapshot, patch.field_name, None) if after_snapshot else None
            events.append(
                EntityStateEventRecord(
                    story_id=story_id,
                    session_id=session_id,
                    entity_id=patch.entity_id,
                    entity_type=patch.entity_type,
                    entity_name=patch.entity_name,
                    field_name=patch.field_name,
                    op=patch.op,
                    value=patch.value,
                    before=before_value,
                    after=after_value,
                    evidence_text=patch.evidence_text,
                    source_turn=patch.source_turn,
                    source=source,
                    operation_id=operation_id,
                    sequence=next_sequence,
                    confidence=patch.confidence,
                    committed_at=datetime.now(),
                )
            )
            next_sequence += 1

        return EntityPatchApplyResult(
            snapshots=list(updated_states),
            items=[item.model_dump(mode="json") for item in updated_states],
            events=events,
            warnings=[],
        )
