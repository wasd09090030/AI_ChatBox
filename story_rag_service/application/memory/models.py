"""记忆编排数据契约。

目标：为 application.memory 内部与调用方提供稳定 TypedDict 约束，
把“分层记忆输入”与“记忆更新事件输出”统一成可序列化结构。

设计原则：
1) 尽量使用宽容字段（total=False）保持链路兼容；
2) 分层字段命名与前端/日志消费语义保持一致；
3) raw_record 字段保留底层管理器原始快照，便于诊断。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class EpisodeRecord(TypedDict, total=False):
    """单条情节记录（episodic 最小持久化单元）。"""
    session_id: str
    world_id: Optional[str]
    role: str
    content: str
    turn_number: int
    created_at: str
    metadata: Dict[str, Any]


class SemanticMemoryRecord(TypedDict, total=False):
    """摘要记忆持久化记录（semantic 层原始快照）。"""
    session_id: str
    world_id: Optional[str]
    summary_text: str
    key_facts: List[str]
    entities: Dict[str, List[str]]
    last_turn: int
    updated_at: str


class ProfileSnapshot(TypedDict, total=False):
    """角色画像快照。

    用于描述长期角色信息，不包含本轮 request-scoped procedural controls。
    """
    persona: Optional[Dict[str, Any]]
    character_card: Optional[Dict[str, Any]]
    story_state: Optional[Dict[str, Any]]


class ProceduralContext(TypedDict, total=False):
    """程序性控制上下文。

    表达“本轮生成如何进行”，例如模式、作者注记、剧本约束、对白控制等。
    """
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
    """MemoryBundle 元信息。

    activation_logs 用于记录“本轮到底激活了哪些记忆来源”，便于可观测性与调试。
    """
    session_id: str
    activation_logs: List[Dict[str, Any]]


class MemoryBundle(TypedDict, total=False):
    """故事生成主流程消费的统一分层记忆包。

    层次顺序并非执行顺序，而是语义分组：episodic/semantic/profile/procedural/world/runtime/entity。
    """
    episodic: MemoryEpisodicLayer
    semantic: MemorySemanticLayer
    profile: MemoryProfileLayer
    procedural: MemoryProceduralLayer
    world: MemoryWorldLayer
    runtime: MemoryRuntimeLayer
    entity: MemoryEntityLayer
    meta: MemoryBundleMeta


class MemoryUpdateEvent(TypedDict, total=False):
    """单条记忆更新事件标准结构。

    事件最终会写入 memory_update_journal，并用于前端时间线展示。
    """
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
    """MemoryOrchestrator 构建结果。

    除 bundle 外额外返回 world_id/activation_logs，供调用侧继续复用。
    """
    bundle: MemoryBundle
    world_id: Optional[str]
    activation_logs: List[Dict[str, Any]]
