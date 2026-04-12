"""文件说明：后端应用层用例编排。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class StoryMemoryOperation(TypedDict, total=False):
    """作用：定义 StoryMemoryOperation 类型，承载本模块核心状态与行为。"""
    operation_id: Optional[str]
    source: Optional[str]
    status: str
    committed_at: Optional[str]
    sequence_min: Optional[int]
    sequence_max: Optional[int]
    event_count: int
    entity_update_count: int


class StoryMemorySemanticView(TypedDict, total=False):
    """作用：定义 StoryMemorySemanticView 数据结构，用于约束字段语义与序列化格式。"""
    summary_memory_snapshot: Optional[Dict[str, Any]]


class StoryMemoryRuntimeView(TypedDict, total=False):
    """作用：定义 StoryMemoryRuntimeView 数据结构，用于约束字段语义与序列化格式。"""
    runtime_state_snapshot: Optional[Dict[str, Any]]


class StoryMemoryEntityView(TypedDict, total=False):
    """作用：定义 StoryMemoryEntityView 数据结构，用于约束字段语义与序列化格式。"""
    entity_state_snapshot: Optional[Dict[str, Any]]
    entity_state_updates: List[Dict[str, Any]]
    world_update: Optional[Dict[str, Any]]


class StoryMemoryTimelineView(TypedDict, total=False):
    """作用：定义 StoryMemoryTimelineView 数据结构，用于约束字段语义与序列化格式。"""
    memory_updates: List[Dict[str, Any]]


class StoryMemoryPayload(TypedDict, total=False):
    """作用：定义 StoryMemoryPayload 数据结构，用于约束字段语义与序列化格式。"""
    session_id: str
    story_id: Optional[str]
    world_id: Optional[str]
    operation: StoryMemoryOperation
    semantic: StoryMemorySemanticView
    runtime: StoryMemoryRuntimeView
    entity: StoryMemoryEntityView
    timeline: StoryMemoryTimelineView
