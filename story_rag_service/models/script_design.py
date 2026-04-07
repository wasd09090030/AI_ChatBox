"""面向世界维度故事大纲的剧本设计模型。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


ScriptDesignStatus = Literal["draft", "active", "archived"]
EventNodeStatus = Literal["pending", "active", "completed", "skipped"]
EventNodeType = Literal["reveal", "conflict", "transition", "climax", "recovery", "setup", "custom"]
ForeshadowStatus = Literal["planted", "hinted", "paid_off", "abandoned"]
ForeshadowCategory = Literal["object", "identity", "prophecy", "relationship", "mystery", "rule", "custom"]
ImportanceLevel = Literal["low", "medium", "high"]


class ScriptGenerationPolicy(BaseModel):
    enforce_stage_order: bool = False
    enforce_pending_event: bool = False
    enforce_foreshadow_tracking: bool = False
    preferred_stage_id: Optional[str] = None
    preferred_event_ids: List[str] = Field(default_factory=list)
    writing_brief: Optional[str] = None


class ScriptStage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1)
    order: int = Field(default=0, ge=0)
    goal: Optional[str] = None
    tension: Optional[str] = None
    entry_condition: Optional[str] = None
    exit_condition: Optional[str] = None
    expected_turning_point: Optional[str] = None
    linked_role_ids: List[str] = Field(default_factory=list)
    linked_lorebook_entry_ids: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ScriptEventNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stage_id: str
    title: str = Field(..., min_length=1)
    summary: Optional[str] = None
    order: int = Field(default=0, ge=0)
    status: EventNodeStatus = "pending"
    event_type: EventNodeType = "custom"
    trigger_condition: Optional[str] = None
    objective: Optional[str] = None
    obstacle: Optional[str] = None
    expected_outcome: Optional[str] = None
    failure_outcome: Optional[str] = None
    scene_hint: Optional[str] = None
    participant_role_ids: List[str] = Field(default_factory=list)
    participant_lorebook_entry_ids: List[str] = Field(default_factory=list)
    prerequisite_event_ids: List[str] = Field(default_factory=list)
    unlocks_event_ids: List[str] = Field(default_factory=list)
    foreshadow_ids: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ForeshadowRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    category: ForeshadowCategory = "custom"
    planted_stage_id: Optional[str] = None
    planted_event_id: Optional[str] = None
    expected_payoff_stage_id: Optional[str] = None
    expected_payoff_event_id: Optional[str] = None
    payoff_description: Optional[str] = None
    status: ForeshadowStatus = "planted"
    importance: ImportanceLevel = "medium"
    notes: Optional[str] = None


class ScriptDesign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str
    title: str = Field(..., min_length=1)
    summary: Optional[str] = None
    logline: Optional[str] = None
    theme: Optional[str] = None
    core_conflict: Optional[str] = None
    ending_direction: Optional[str] = None
    protagonist_profile: Optional[str] = None
    tone_style: Optional[str] = None
    status: ScriptDesignStatus = "draft"
    stage_outlines: List[ScriptStage] = Field(default_factory=list)
    event_nodes: List[ScriptEventNode] = Field(default_factory=list)
    foreshadows: List[ForeshadowRecord] = Field(default_factory=list)
    default_generation_policy: ScriptGenerationPolicy = Field(default_factory=ScriptGenerationPolicy)
    tags: List[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScriptDesignCreate(BaseModel):
    world_id: str
    title: str = Field(..., min_length=1)
    summary: Optional[str] = None
    logline: Optional[str] = None
    theme: Optional[str] = None
    core_conflict: Optional[str] = None
    ending_direction: Optional[str] = None
    protagonist_profile: Optional[str] = None
    tone_style: Optional[str] = None
    status: ScriptDesignStatus = "draft"
    stage_outlines: List[ScriptStage] = Field(default_factory=list)
    event_nodes: List[ScriptEventNode] = Field(default_factory=list)
    foreshadows: List[ForeshadowRecord] = Field(default_factory=list)
    default_generation_policy: ScriptGenerationPolicy = Field(default_factory=ScriptGenerationPolicy)
    tags: List[str] = Field(default_factory=list)


class ScriptDesignUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    summary: Optional[str] = None
    logline: Optional[str] = None
    theme: Optional[str] = None
    core_conflict: Optional[str] = None
    ending_direction: Optional[str] = None
    protagonist_profile: Optional[str] = None
    tone_style: Optional[str] = None
    status: Optional[ScriptDesignStatus] = None
    stage_outlines: Optional[List[ScriptStage]] = None
    event_nodes: Optional[List[ScriptEventNode]] = None
    foreshadows: Optional[List[ForeshadowRecord]] = None
    default_generation_policy: Optional[ScriptGenerationPolicy] = None
    tags: Optional[List[str]] = None
    version: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def ensure_non_empty_patch(self) -> "ScriptDesignUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self