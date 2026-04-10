from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import StoryMemoryPayload


def _pick_operation_id(
    *,
    memory_updates: List[Dict[str, Any]],
    entity_state_updates: List[Dict[str, Any]],
    world_update: Optional[Dict[str, Any]],
) -> Optional[str]:
    candidates = [
        *((item.get("operation_id") for item in entity_state_updates if item.get("operation_id"))),
        *((item.get("operation_id") for item in memory_updates if item.get("operation_id"))),
        world_update.get("operation_id") if isinstance(world_update, dict) else None,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def _pick_operation_source(
    *,
    memory_updates: List[Dict[str, Any]],
    entity_state_updates: List[Dict[str, Any]],
) -> Optional[str]:
    for item in entity_state_updates:
        source = item.get("source")
        if source:
            return str(source)
    for item in memory_updates:
        source = item.get("source")
        if source:
            return str(source)
    return None


def _pick_operation_status(
    *,
    memory_updates: List[Dict[str, Any]],
    entity_state_updates: List[Dict[str, Any]],
) -> str:
    statuses = [
        *(str(item.get("status") or "") for item in memory_updates),
        *(str(item.get("status") or "") for item in entity_state_updates),
    ]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "stale" for status in statuses):
        return "stale"
    return "committed"


def _pick_operation_time(
    *,
    summary_memory_snapshot: Optional[Dict[str, Any]],
    memory_updates: List[Dict[str, Any]],
    entity_state_updates: List[Dict[str, Any]],
    world_update: Optional[Dict[str, Any]],
) -> Optional[str]:
    candidates = [
        *((item.get("committed_at") for item in entity_state_updates if item.get("committed_at"))),
        *((item.get("committed_at") for item in memory_updates if item.get("committed_at"))),
        world_update.get("updated_at") if isinstance(world_update, dict) else None,
        summary_memory_snapshot.get("updated_at") if isinstance(summary_memory_snapshot, dict) else None,
    ]
    normalized = [str(item) for item in candidates if item]
    return max(normalized) if normalized else None


def _pick_sequence_range(
    *,
    memory_updates: List[Dict[str, Any]],
    entity_state_updates: List[Dict[str, Any]],
) -> tuple[Optional[int], Optional[int]]:
    sequences: List[int] = []
    for item in [*memory_updates, *entity_state_updates]:
        value = item.get("sequence")
        if isinstance(value, int):
            sequences.append(value)
    if not sequences:
        return None, None
    return min(sequences), max(sequences)


def build_story_memory_payload(
    *,
    session_id: str,
    story_id: Optional[str] = None,
    world_id: Optional[str] = None,
    summary_memory_snapshot: Optional[Dict[str, Any]] = None,
    runtime_state_snapshot: Optional[Dict[str, Any]] = None,
    entity_state_snapshot: Optional[Dict[str, Any]] = None,
    entity_state_updates: Optional[List[Dict[str, Any]]] = None,
    world_update: Optional[Dict[str, Any]] = None,
    memory_updates: Optional[List[Dict[str, Any]]] = None,
) -> StoryMemoryPayload:
    normalized_memory_updates = list(memory_updates or [])
    normalized_entity_updates = list(entity_state_updates or [])
    sequence_min, sequence_max = _pick_sequence_range(
        memory_updates=normalized_memory_updates,
        entity_state_updates=normalized_entity_updates,
    )
    return {
        "session_id": session_id,
        "story_id": story_id,
        "world_id": world_id,
        "operation": {
            "operation_id": _pick_operation_id(
                memory_updates=normalized_memory_updates,
                entity_state_updates=normalized_entity_updates,
                world_update=world_update,
            ),
            "source": _pick_operation_source(
                memory_updates=normalized_memory_updates,
                entity_state_updates=normalized_entity_updates,
            ),
            "status": _pick_operation_status(
                memory_updates=normalized_memory_updates,
                entity_state_updates=normalized_entity_updates,
            ),
            "committed_at": _pick_operation_time(
                summary_memory_snapshot=summary_memory_snapshot,
                memory_updates=normalized_memory_updates,
                entity_state_updates=normalized_entity_updates,
                world_update=world_update,
            ),
            "sequence_min": sequence_min,
            "sequence_max": sequence_max,
            "event_count": len(normalized_memory_updates),
            "entity_update_count": len(normalized_entity_updates),
        },
        "semantic": {
            "summary_memory_snapshot": summary_memory_snapshot,
        },
        "runtime": {
            "runtime_state_snapshot": runtime_state_snapshot,
        },
        "entity": {
            "entity_state_snapshot": entity_state_snapshot,
            "entity_state_updates": normalized_entity_updates,
            "world_update": world_update,
        },
        "timeline": {
            "memory_updates": normalized_memory_updates,
        },
    }
