"""实体状态 patch 与事件流模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field

from .entity_state import EntityType, EntityStateSnapshot


# 变量作用：变量 EntityPatchField，用于保存 entitypatchfield 相关模块级状态。
EntityPatchField = Literal[
    "current_location",
    "inventory",
    "status_tags",
    "companions",
    "short_goal",
    "state_summary",
]
# 变量作用：变量 EntityPatchOp，用于保存 entitypatchop 相关模块级状态。
EntityPatchOp = Literal["set", "add", "remove", "clear", "reset"]
# 变量作用：变量 EntityPatchStatus，用于保存 entitypatchstatus 相关模块级状态。
EntityPatchStatus = Literal["committed", "failed", "skipped"]


class EntityStatePatch(BaseModel):
    """单条实体字段 patch。"""

    entity_id: str
    entity_type: EntityType = "character"
    entity_name: Optional[str] = None
    field_name: EntityPatchField
    op: EntityPatchOp
    value: Any = None
    evidence_text: Optional[str] = None
    source_turn: Optional[int] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityPatchExtractionResult(BaseModel):
    """结构化 patch 抽取结果。"""

    patches: List[EntityStatePatch] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class EntityPatchApplyResult(BaseModel):
    """patch 应用结果。"""

    snapshots: List[EntityStateSnapshot] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    events: List["EntityStateEventRecord"] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class EntityStateEventRecord(BaseModel):
    """持久化的实体状态事件记录。"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    story_id: str
    session_id: str
    entity_id: str
    entity_type: EntityType = "character"
    entity_name: Optional[str] = None
    field_name: EntityPatchField
    op: EntityPatchOp
    value: Any = None
    before: Any = None
    after: Any = None
    evidence_text: Optional[str] = None
    source_turn: Optional[int] = None
    source: str = "entity_patch"
    operation_id: Optional[str] = None
    sequence: Optional[int] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: EntityPatchStatus = "committed"
    committed_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


EntityPatchApplyResult.model_rebuild()
