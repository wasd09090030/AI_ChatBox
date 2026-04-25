"""实体状态 API 响应序列化辅助。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Optional, Sequence

from models.entity_state import (
    EntityStateCollection,
    EntityStateRebuildResponse,
    EntityStateSnapshot,
)


def build_entity_display_name_map(states: Sequence[EntityStateSnapshot]) -> Dict[str, str]:
    """从实体快照列表构建 entity_id -> display_name 映射。"""
    display_name_map: Dict[str, str] = {}
    for state in states:
        entity_id = str(getattr(state, "entity_id", "") or "").strip()
        display_name = str(getattr(state, "display_name", "") or "").strip()
        if entity_id and display_name:
            display_name_map[entity_id] = display_name
    return display_name_map


def serialize_companion_value(
    value: Any,
    *,
    display_name_map: Mapping[str, str],
) -> Any:
    """将 companions 字段值富化为 {id, display_name} 结构。"""
    if value is None:
        return None

    if isinstance(value, list):
        normalized_items = []
        for item in value:
            normalized = serialize_companion_value(item, display_name_map=display_name_map)
            if normalized is None:
                continue
            normalized_items.append(normalized)
        return normalized_items

    if isinstance(value, str):
        companion_id = value.strip()
        if not companion_id:
            return None
        return {
            "id": companion_id,
            "display_name": display_name_map.get(companion_id) or companion_id,
        }

    if isinstance(value, Mapping):
        companion_id = str(value.get("id") or "").strip()
        display_name = str(value.get("display_name") or "").strip()
        if not companion_id and not display_name:
            return dict(value)
        resolved_name = display_name or display_name_map.get(companion_id) or companion_id
        payload = dict(value)
        if companion_id:
            payload["id"] = companion_id
        if resolved_name:
            payload["display_name"] = resolved_name
        return payload

    return value


def serialize_memory_event_payload(
    payload: Optional[Dict[str, Any]],
    *,
    display_name_map: Mapping[str, str],
    field_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """递归富化 memory / patch 负载中的 companions 字段。"""
    if payload is None:
        return None
    return _serialize_value(payload, display_name_map=display_name_map, field_name=field_name)


def serialize_entity_state_snapshot(
    state: EntityStateSnapshot,
    *,
    display_name_map: Mapping[str, str],
) -> Dict[str, Any]:
    """将内部实体快照转换为 API 输出结构。"""
    payload = state.model_dump(mode="json")
    payload["companions"] = serialize_companion_value(
        payload.get("companions") or [],
        display_name_map=display_name_map,
    )
    return payload


def serialize_entity_state_collection(
    collection: EntityStateCollection,
) -> Dict[str, Any]:
    """将内部实体集合转换为 API 输出结构。"""
    return serialize_entity_state_collection_payload(
        story_id=collection.story_id,
        session_id=collection.session_id,
        entity_type=collection.entity_type,
        items=collection.items,
    )


def serialize_entity_state_collection_payload(
    *,
    story_id: Optional[str],
    session_id: str,
    entity_type: Optional[str],
    items: Sequence[EntityStateSnapshot],
) -> Dict[str, Any]:
    """按 story/session 维度序列化实体状态列表。"""
    normalized_items = list(items)
    display_name_map = build_entity_display_name_map(normalized_items)
    return {
        "story_id": story_id,
        "session_id": session_id,
        "entity_type": entity_type,
        "items": [
            serialize_entity_state_snapshot(item, display_name_map=display_name_map)
            for item in normalized_items
        ],
        "total": len(normalized_items),
    }


def serialize_entity_state_rebuild_response(
    response: EntityStateRebuildResponse,
) -> Dict[str, Any]:
    """将内部重建结果转换为 API 输出结构。"""
    collection_payload = serialize_entity_state_collection_payload(
        story_id=response.story_id,
        session_id=response.session_id,
        entity_type=None,
        items=response.items,
    )
    display_name_map = build_entity_display_name_map(response.items)
    return {
        "story_id": response.story_id,
        "session_id": response.session_id,
        "rebuilt": response.rebuilt,
        "entity_count": response.entity_count,
        "memory_updates": [
            serialize_memory_event_payload(update, display_name_map=display_name_map)
            for update in list(response.memory_updates or [])
        ],
        "warnings": list(response.warnings or []),
        "items": collection_payload["items"],
    }


def _serialize_value(
    value: Any,
    *,
    display_name_map: Mapping[str, str],
    field_name: Optional[str],
) -> Any:
    if field_name == "companions":
        return serialize_companion_value(value, display_name_map=display_name_map)

    if isinstance(value, list):
        return [
            _serialize_value(item, display_name_map=display_name_map, field_name=field_name)
            for item in value
        ]

    if not isinstance(value, Mapping):
        return value

    payload = dict(value)
    normalized_field_name = str(payload.get("field_name") or payload.get("field") or field_name or "").strip() or None
    normalized_payload: Dict[str, Any] = {}
    for key, nested_value in payload.items():
        next_field_name = normalized_field_name if key in {"value", "before", "after"} else (key if key == "companions" else None)
        normalized_payload[key] = _serialize_value(
            nested_value,
            display_name_map=display_name_map,
            field_name=next_field_name,
        )
    return normalized_payload
