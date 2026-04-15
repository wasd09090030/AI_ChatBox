"""story_memory 读模型契约定义。

这些 TypedDict 用于约束后端返回载荷结构，减少前后端字段语义漂移。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class StoryMemoryOperation(TypedDict, total=False):
    """本轮记忆操作元信息。"""
    operation_id: Optional[str]
    source: Optional[str]
    status: str
    committed_at: Optional[str]
    sequence_min: Optional[int]
    sequence_max: Optional[int]
    event_count: int
    entity_update_count: int


class StoryMemorySemanticView(TypedDict, total=False):
    """语义记忆视图（摘要快照）。"""
    summary_memory_snapshot: Optional[Dict[str, Any]]


class StoryMemoryRuntimeView(TypedDict, total=False):
    """运行时状态视图。"""
    runtime_state_snapshot: Optional[Dict[str, Any]]


class StoryMemoryEntityView(TypedDict, total=False):
    """实体状态视图（快照 + 增量更新）。"""
    entity_state_snapshot: Optional[Dict[str, Any]]
    entity_state_updates: List[Dict[str, Any]]
    world_update: Optional[Dict[str, Any]]


class StoryMemoryTimelineView(TypedDict, total=False):
    """记忆时间线视图。"""
    memory_updates: List[Dict[str, Any]]


class StoryMemoryPayload(TypedDict, total=False):
    """聚合后的 story_memory 返回载荷。

    对应前端结构分组：operation / semantic / runtime / entity / timeline。
    """
    session_id: str
    story_id: Optional[str]
    world_id: Optional[str]
    operation: StoryMemoryOperation
    semantic: StoryMemorySemanticView
    runtime: StoryMemoryRuntimeView
    entity: StoryMemoryEntityView
    timeline: StoryMemoryTimelineView
