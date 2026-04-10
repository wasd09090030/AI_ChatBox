from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class StoryMemoryOperation(TypedDict, total=False):
    operation_id: Optional[str]
    source: Optional[str]
    status: str
    committed_at: Optional[str]
    sequence_min: Optional[int]
    sequence_max: Optional[int]
    event_count: int
    entity_update_count: int


class StoryMemorySemanticView(TypedDict, total=False):
    summary_memory_snapshot: Optional[Dict[str, Any]]


class StoryMemoryRuntimeView(TypedDict, total=False):
    runtime_state_snapshot: Optional[Dict[str, Any]]


class StoryMemoryEntityView(TypedDict, total=False):
    entity_state_snapshot: Optional[Dict[str, Any]]
    entity_state_updates: List[Dict[str, Any]]
    world_update: Optional[Dict[str, Any]]


class StoryMemoryTimelineView(TypedDict, total=False):
    memory_updates: List[Dict[str, Any]]


class StoryMemoryPayload(TypedDict, total=False):
    session_id: str
    story_id: Optional[str]
    world_id: Optional[str]
    operation: StoryMemoryOperation
    semantic: StoryMemorySemanticView
    runtime: StoryMemoryRuntimeView
    entity: StoryMemoryEntityView
    timeline: StoryMemoryTimelineView
