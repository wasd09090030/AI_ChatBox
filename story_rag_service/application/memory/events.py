"""文件说明：后端应用层用例编排。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from .models import MemoryUpdateEvent


def build_memory_operation_id(source: str) -> str:
    """功能：构建记忆操作 ID。"""
    normalized = (source or "memory").strip() or "memory"
    return f"{normalized}:{uuid.uuid4()}"


def infer_memory_display_kind(
    *,
    memory_layer: str,
    action: str,
    status: str = "committed",
) -> str:
    """功能：推断记忆 display 类型。"""
    if status == "failed":
        return "failed"
    if memory_layer == "semantic":
        if action == "reset":
            return "semantic_reset"
        if action == "marked_stale":
            return "semantic_stale"
        return "semantic_update"
    if memory_layer == "episodic":
        if action == "rebuilt":
            return "session_rebuild"
        if action == "reindexed":
            return "index_rebuild"
        return "write"
    return "write"


def finalize_memory_update_events(
    events: Iterable[MemoryUpdateEvent],
    *,
    operation_id: Optional[str] = None,
    sequence_start: int = 1,
) -> list[MemoryUpdateEvent]:
    """功能：收敛并完成记忆 update 事件。"""
    event_list = list(events)
    if not event_list:
        return event_list

    normalized_operation_id = operation_id or build_memory_operation_id(event_list[0].get("source", "memory"))
    next_sequence = max(1, int(sequence_start))

    for event in event_list:
        if not event.get("operation_id"):
            event["operation_id"] = normalized_operation_id
        if event.get("sequence") is None:
            event["sequence"] = next_sequence
        next_sequence = int(event["sequence"]) + 1
        if not event.get("display_kind"):
            event["display_kind"] = infer_memory_display_kind(
                memory_layer=event.get("memory_layer") or "unknown",
                action=event.get("action") or "updated",
                status=event.get("status") or "committed",
            )

    return event_list


def build_memory_update_event(
    *,
    session_id: str,
    memory_layer: str,
    action: str,
    source: str,
    title: str,
    source_turn: Optional[int] = None,
    memory_key: Optional[str] = None,
    reason: Optional[str] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    status: str = "committed",
    operation_id: Optional[str] = None,
    sequence: Optional[int] = None,
    display_kind: Optional[str] = None,
) -> MemoryUpdateEvent:
    """功能：构建记忆 update 事件。"""
    return {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "operation_id": operation_id,
        "sequence": sequence,
        "display_kind": display_kind,
        "memory_layer": memory_layer,
        "action": action,
        "source": source,
        "source_turn": source_turn,
        "memory_key": memory_key,
        "title": title,
        "reason": reason,
        "before": before,
        "after": after,
        "status": status,
        "committed_at": datetime.now().isoformat(),
    }


def summarize_summary_snapshot(snapshot: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """提炼摘要快照关键字段，生成用于日志/事件记录的精简视图。"""
    if not snapshot:
        return None

    return {
        "summary_text": str(snapshot.get("summary_text") or "")[:240],
        "key_facts": list(snapshot.get("key_facts") or [])[:12],
        "last_turn": snapshot.get("last_turn"),
        "updated_at": snapshot.get("updated_at"),
    }
