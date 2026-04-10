from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class EpisodeRecord(TypedDict, total=False):
    session_id: str
    world_id: Optional[str]
    role: str
    content: str
    turn_number: int
    created_at: str
    metadata: Dict[str, Any]


class SemanticMemoryRecord(TypedDict, total=False):
    session_id: str
    world_id: Optional[str]
    summary_text: str
    key_facts: List[str]
    entities: Dict[str, List[str]]
    last_turn: int
    updated_at: str


class ProfileSnapshot(TypedDict, total=False):
    persona: Optional[Dict[str, Any]]
    character_card: Optional[Dict[str, Any]]
    story_state: Optional[Dict[str, Any]]


class ProceduralContext(TypedDict, total=False):
    authors_note: Optional[str]
    dialogue_controls: Dict[str, Any]
    script_guidance: Dict[str, Any]
    mode: str
    instruction: Optional[str]
    focus_instruction: Optional[str]
    focus_label: Optional[str]


class MemoryEpisodicLayer(TypedDict, total=False):
    recent_messages: List[Dict[str, Any]]
    recalled_episodes: List[Dict[str, Any]]


class MemorySemanticLayer(TypedDict, total=False):
    summary_text: str
    key_facts: List[str]
    entities: Dict[str, Any]
    raw_record: Optional[SemanticMemoryRecord]


class MemoryProfileLayer(TypedDict, total=False):
    persona: Optional[Dict[str, Any]]
    character_card: Optional[Dict[str, Any]]
    story_state: Optional[Dict[str, Any]]
    raw_profile: Dict[str, Any]


class MemoryProceduralLayer(TypedDict, total=False):
    authors_note: Optional[str]
    dialogue_controls: Dict[str, Any]
    script_guidance: Dict[str, Any]
    mode: str
    instruction: Optional[str]
    focus_instruction: Optional[str]
    focus_label: Optional[str]
    script_design_context: Dict[str, Any]


class MemoryWorldLayer(TypedDict, total=False):
    world_id: Optional[str]
    retrieved_lore: List[Dict[str, Any]]
    world_config: Dict[str, Any]


class MemoryRuntimeLayer(TypedDict, total=False):
    story_id: Optional[str]
    runtime_state_id: Optional[str]
    current_stage_id: Optional[str]
    current_event_id: Optional[str]
    creation_mode: Optional[str]
    raw_record: Optional[Dict[str, Any]]


class MemoryEntityLayer(TypedDict, total=False):
    story_id: Optional[str]
    entity_type: Optional[str]
    tracked_entities: int
    entity_state_snapshot: Optional[Dict[str, Any]]
    recent_entity_updates: List[Dict[str, Any]]
    raw_record: Optional[Dict[str, Any]]


class MemoryBundleMeta(TypedDict, total=False):
    session_id: str
    activation_logs: List[Dict[str, Any]]


class MemoryBundle(TypedDict, total=False):
    episodic: MemoryEpisodicLayer
    semantic: MemorySemanticLayer
    profile: MemoryProfileLayer
    procedural: MemoryProceduralLayer
    world: MemoryWorldLayer
    runtime: MemoryRuntimeLayer
    entity: MemoryEntityLayer
    meta: MemoryBundleMeta


class MemoryUpdateEvent(TypedDict, total=False):
    event_id: str
    session_id: str
    operation_id: str
    sequence: int
    display_kind: str
    memory_layer: str
    action: str
    source: str
    source_turn: Optional[int]
    memory_key: Optional[str]
    title: str
    reason: Optional[str]
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    status: str
    committed_at: str


class MemoryOrchestratorResult(TypedDict):
    bundle: MemoryBundle
    world_id: Optional[str]
    activation_logs: List[Dict[str, Any]]
