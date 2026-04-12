"""双模式故事创作的剧本运行时状态模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field


# 变量 CreationMode，用于保存 creationmode 相关模块级状态。
CreationMode = Literal["improv", "scripted"]
# 变量 ProgressIntent，用于保存 progressintent 相关模块级状态。
ProgressIntent = Literal["hold", "advance", "complete"]


class ScriptRuntimeState(BaseModel):
    """绑定剧本设计后的故事运行时真值状态。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    story_id: str
    session_id: str
    world_id: Optional[str] = None
    script_design_id: str
    creation_mode: CreationMode = "improv"
    current_stage_id: Optional[str] = None
    current_event_id: Optional[str] = None
    completed_event_ids: List[str] = Field(default_factory=list)
    skipped_event_ids: List[str] = Field(default_factory=list)
    active_foreshadow_ids: List[str] = Field(default_factory=list)
    paid_off_foreshadow_ids: List[str] = Field(default_factory=list)
    abandoned_foreshadow_ids: List[str] = Field(default_factory=list)
    current_location_entry_id: Optional[str] = None
    current_time_label: Optional[str] = None
    active_character_entry_ids: List[str] = Field(default_factory=list)
    runtime_notes: Optional[str] = None
    last_contract_snapshot: Optional[Dict[str, Any]] = None
    last_check_result: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScriptRuntimeStateUpdate(BaseModel):
    """故事运行时状态的增量更新模型。"""

    script_design_id: Optional[str] = None
    creation_mode: Optional[CreationMode] = None
    current_stage_id: Optional[str] = None
    current_event_id: Optional[str] = None
    completed_event_ids: Optional[List[str]] = None
    skipped_event_ids: Optional[List[str]] = None
    active_foreshadow_ids: Optional[List[str]] = None
    paid_off_foreshadow_ids: Optional[List[str]] = None
    abandoned_foreshadow_ids: Optional[List[str]] = None
    current_location_entry_id: Optional[str] = None
    current_time_label: Optional[str] = None
    active_character_entry_ids: Optional[List[str]] = None
    runtime_notes: Optional[str] = None
    last_contract_snapshot: Optional[Dict[str, Any]] = None
    last_check_result: Optional[Dict[str, Any]] = None


class ScriptRoundContract(BaseModel):
    """严格模式生成前使用的内部回合合同。"""

    creation_mode: CreationMode = "scripted"
    script_design_id: str
    stage_id: Optional[str] = None
    event_id: Optional[str] = None
    stage_title: Optional[str] = None
    event_title: Optional[str] = None
    stage_goal: Optional[str] = None
    event_objective: Optional[str] = None
    event_obstacle: Optional[str] = None
    allowed_character_ids: List[str] = Field(default_factory=list)
    allowed_location_ids: List[str] = Field(default_factory=list)
    required_foreshadow_ids: List[str] = Field(default_factory=list)
    highlighted_foreshadows: List[Dict[str, Any]] = Field(default_factory=list)
    rag_scope_entry_ids: List[str] = Field(default_factory=list)
    progress_intent: ProgressIntent = "hold"
    completion_guard: Optional[str] = None


class ScriptConsistencyCheckResult(BaseModel):
    """严格模式生成的一致性检查结果。"""

    passed: bool = True
    stage_alignment: Literal["pass", "warn", "fail"] = "pass"
    event_alignment: Literal["pass", "warn", "fail"] = "pass"
    foreshadow_alignment: Literal["pass", "warn", "fail"] = "pass"
    unauthorized_entities: List[str] = Field(default_factory=list)
    premature_payoff_ids: List[str] = Field(default_factory=list)
    unsupported_completion: bool = False
    notes: List[str] = Field(default_factory=list)
