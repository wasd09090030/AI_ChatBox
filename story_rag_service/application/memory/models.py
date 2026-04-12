"""记忆编排相关的数据模型定义。

本文件描述 MemoryBundle 的分层结构，以及记忆更新事件的统一数据形态。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class EpisodeRecord(TypedDict, total=False):
    """单条情节记录（episodic 层的最小单元）。"""
    session_id: str
    world_id: Optional[str]
    role: str
    content: str
    turn_number: int
    created_at: str
    metadata: Dict[str, Any]


class SemanticMemoryRecord(TypedDict, total=False):
    """摘要记忆持久化记录。"""
    session_id: str
    world_id: Optional[str]
    summary_text: str
    key_facts: List[str]
    entities: Dict[str, List[str]]
    last_turn: int
    updated_at: str


class ProfileSnapshot(TypedDict, total=False):
    """角色画像快照（persona/character_card/story_state）。"""
    persona: Optional[Dict[str, Any]]
    character_card: Optional[Dict[str, Any]]
    story_state: Optional[Dict[str, Any]]


class ProceduralContext(TypedDict, total=False):
    """程序性控制上下文（模式、作者注记、焦点指令等）。"""
    authors_note: Optional[str]
    dialogue_controls: Dict[str, Any]
    script_guidance: Dict[str, Any]
    mode: str
    instruction: Optional[str]
    focus_instruction: Optional[str]
    focus_label: Optional[str]


class MemoryEpisodicLayer(TypedDict, total=False):
    """MemoryBundle 的情节记忆层。"""
    recent_messages: List[Dict[str, Any]]
    recalled_episodes: List[Dict[str, Any]]


class MemorySemanticLayer(TypedDict, total=False):
    """MemoryBundle 的语义摘要层。"""
    summary_text: str
    key_facts: List[str]
    entities: Dict[str, Any]
    raw_record: Optional[SemanticMemoryRecord]


class MemoryProfileLayer(TypedDict, total=False):
    """MemoryBundle 的角色画像层。"""
    persona: Optional[Dict[str, Any]]
    character_card: Optional[Dict[str, Any]]
    story_state: Optional[Dict[str, Any]]
    raw_profile: Dict[str, Any]


class MemoryProceduralLayer(TypedDict, total=False):
    """MemoryBundle 的程序控制层。"""
    authors_note: Optional[str]
    dialogue_controls: Dict[str, Any]
    script_guidance: Dict[str, Any]
    mode: str
    instruction: Optional[str]
    focus_instruction: Optional[str]
    focus_label: Optional[str]
    script_design_context: Dict[str, Any]


class MemoryWorldLayer(TypedDict, total=False):
    """MemoryBundle 的世界观上下文层。"""
    world_id: Optional[str]
    retrieved_lore: List[Dict[str, Any]]
    world_config: Dict[str, Any]


class MemoryRuntimeLayer(TypedDict, total=False):
    """MemoryBundle 的运行时状态层。"""
    story_id: Optional[str]
    runtime_state_id: Optional[str]
    current_stage_id: Optional[str]
    current_event_id: Optional[str]
    creation_mode: Optional[str]
    raw_record: Optional[Dict[str, Any]]


class MemoryEntityLayer(TypedDict, total=False):
    """MemoryBundle 的实体状态层。"""
    story_id: Optional[str]
    entity_type: Optional[str]
    tracked_entities: int
    entity_state_snapshot: Optional[Dict[str, Any]]
    recent_entity_updates: List[Dict[str, Any]]
    raw_record: Optional[Dict[str, Any]]


class MemoryBundleMeta(TypedDict, total=False):
    """MemoryBundle 元信息（会话标识与激活日志）。"""
    session_id: str
    activation_logs: List[Dict[str, Any]]


class MemoryBundle(TypedDict, total=False):
    """故事生成主流程消费的统一分层记忆包。"""
    episodic: MemoryEpisodicLayer
    semantic: MemorySemanticLayer
    profile: MemoryProfileLayer
    procedural: MemoryProceduralLayer
    world: MemoryWorldLayer
    runtime: MemoryRuntimeLayer
    entity: MemoryEntityLayer
    meta: MemoryBundleMeta


class MemoryUpdateEvent(TypedDict, total=False):
    """单条记忆更新事件的标准结构。"""
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
    """MemoryOrchestrator 构建结果。"""
    bundle: MemoryBundle
    world_id: Optional[str]
    activation_logs: List[Dict[str, Any]]
