"""用于结构化故事实体追踪的实体状态模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# 变量 EntityType，用于保存 entitytype 相关模块级状态。
EntityType = Literal["character"]


class EntityStateSnapshot(BaseModel):
    """单个故事实体的当前结构化状态。"""

    story_id: str
    session_id: str
    entity_id: str
    entity_type: EntityType = "character"
    display_name: str
    current_location: Optional[str] = None
    inventory: List[str] = Field(default_factory=list)
    status_tags: List[str] = Field(default_factory=list)
    companions: List[str] = Field(default_factory=list)
    short_goal: Optional[str] = None
    state_summary: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    last_source_turn: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityStateCollection(BaseModel):
    """故事/会话维度实体状态列表响应。"""

    story_id: Optional[str] = None
    session_id: str
    entity_type: Optional[EntityType] = None
    items: List[EntityStateSnapshot] = Field(default_factory=list)
    total: int = 0


class EntityStateRebuildResponse(BaseModel):
    """实体状态重建响应载荷。"""

    story_id: Optional[str] = None
    session_id: str
    rebuilt: bool = False
    entity_count: int = 0
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    items: List[EntityStateSnapshot] = Field(default_factory=list)
