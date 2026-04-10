"""故事生成 v2 相关 schema 定义。"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class V2GenerateRequest(BaseModel):
    """故事生成 v2 请求。"""
    session_id: str = Field(..., description="Session identifier")
    story_id: Optional[str] = Field(default=None, description="Bound story ID")
    thread_id: Optional[str] = Field(default=None, description="Optional LangGraph thread ID for checkpointing")
    user_input: str = Field(..., description="User's latest input/action")
    world_id: Optional[str] = Field(default=None, description="Target world ID")
    creation_mode: Literal["improv", "scripted"] = Field(default="improv")
    progress_intent: Literal["hold", "advance", "complete"] = Field(default="hold")
    runtime_state_id: Optional[str] = Field(default=None)
    allow_state_transition: bool = Field(default=True)

    model: Optional[str] = Field(default=None, description="LLM model name")
    provider: Optional[str] = Field(default=None, description="AI provider key (e.g. deepseek, qwen, openai)")
    base_url: Optional[str] = Field(default=None, description="Provider base URL override (optional)")
    temperature: Optional[float] = Field(default=0.8, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=32000)

    use_rag: bool = Field(default=True, description="Whether to use RAG")
    top_k: Optional[int] = Field(default=5, description="Top-k retrieval")

    style: Optional[str] = Field(default="narrative", description="Writing style")
    language: str = Field(default="zh-CN", description="Output language")
    character_card_id: Optional[str] = Field(default=None, description="Bound character card ID for roleplay")
    persona_id: Optional[str] = Field(default=None, description="Bound user persona ID for roleplay")
    story_state_mode: Optional[str] = Field(
        default=None,
        description="Story state strategy: off|light|strict (reserved for RP pipeline)",
    )

    # --- SillyTavern-inspired story control fields ---
    authors_note: Optional[str] = Field(
        default=None,
        description="Author's Note injected near recent context to steer the narrative",
    )
    mode: Optional[Literal["narrative", "choices", "instruction"]] = Field(
        default="narrative",
        description="Generation mode: narrative (default), choices (AI appends [A][B][C] options), instruction (force a plot directive)",
    )
    instruction: Optional[str] = Field(
        default=None,
        description="Forced plot instruction injected when mode='instruction'",
    )
    selected_context_entry_ids: List[str] = Field(
        default_factory=list,
        description="Explicit lorebook entry IDs selected by the user for this round",
    )
    script_design_id: Optional[str] = Field(
        default=None,
        description="Selected script design ID for this round",
    )
    active_stage_id: Optional[str] = Field(
        default=None,
        description="Selected script stage ID for this round",
    )
    active_event_id: Optional[str] = Field(
        default=None,
        description="Selected script event ID for this round",
    )
    follow_script_design: bool = Field(
        default=False,
        description="Whether generation should follow the selected script design guidance",
    )
    principal_character_id: Optional[str] = Field(
        default=None,
        description="Selected lorebook character entry promoted as the principal dialogue character for this round",
    )
    dialogue_mode: Optional[Literal["auto", "focused", "required"]] = Field(
        default="auto",
        description="Principal character dialogue mode",
    )
    dialogue_target: Optional[str] = Field(
        default=None,
        description="Dialogue target such as protagonist, another role, or a group",
    )
    dialogue_intent: Optional[str] = Field(
        default=None,
        description="Dialogue purpose such as reveal information or escalate conflict",
    )
    dialogue_style_hint: Optional[str] = Field(
        default=None,
        description="Round-specific dialogue style hint",
    )
    force_dialogue_round: bool = Field(
        default=False,
        description="Whether this round must include principal character dialogue",
    )
    focus_instruction: Optional[str] = Field(
        default=None,
        description="Round-specific focus instruction chosen by the user",
    )
    focus_label: Optional[str] = Field(
        default=None,
        description="Display label for the selected round-specific focus instruction",
    )
    enhance_input: bool = Field(
        default=False,
        description="Whether to enhance short user input before generation",
    )


class V2InputEnhancementPreviewRequest(BaseModel):
    """生成前输入增强预览请求。"""
    session_id: str = Field(..., description="Session identifier")
    story_id: Optional[str] = Field(default=None, description="Bound story ID")
    user_input: str = Field(..., description="User input to preview")
    world_id: Optional[str] = Field(default=None, description="Target world ID")
    creation_mode: Literal["improv", "scripted"] = Field(default="improv")
    progress_intent: Literal["hold", "advance", "complete"] = Field(default="hold")
    runtime_state_id: Optional[str] = Field(default=None)
    allow_state_transition: bool = Field(default=False)
    model: Optional[str] = Field(default=None, description="LLM model name")
    provider: Optional[str] = Field(default=None, description="AI provider key")
    base_url: Optional[str] = Field(default=None, description="Provider base URL override")
    temperature: Optional[float] = Field(default=0.8, ge=0, le=2)
    character_card_id: Optional[str] = Field(default=None, description="Bound character card ID for roleplay")
    persona_id: Optional[str] = Field(default=None, description="Bound user persona ID for roleplay")
    selected_context_entry_ids: List[str] = Field(default_factory=list, description="Explicit lorebook entry IDs selected by the user")
    script_design_id: Optional[str] = Field(default=None, description="Selected script design ID for this round")
    active_stage_id: Optional[str] = Field(default=None, description="Selected script stage ID for this round")
    active_event_id: Optional[str] = Field(default=None, description="Selected script event ID for this round")
    follow_script_design: bool = Field(default=False, description="Whether generation should follow the selected script design guidance")
    principal_character_id: Optional[str] = Field(default=None, description="Principal lorebook character entry ID for this round")
    dialogue_mode: Optional[Literal["auto", "focused", "required"]] = Field(default="auto", description="Principal character dialogue mode")
    dialogue_target: Optional[str] = Field(default=None, description="Dialogue target")
    dialogue_intent: Optional[str] = Field(default=None, description="Dialogue purpose")
    dialogue_style_hint: Optional[str] = Field(default=None, description="Dialogue style hint")
    force_dialogue_round: bool = Field(default=False, description="Whether this round must include principal character dialogue")
    focus_instruction: Optional[str] = Field(default=None, description="Round-specific focus instruction chosen by the user")
    focus_label: Optional[str] = Field(default=None, description="Display label for the selected focus instruction")


class V2InputEnhancementPreviewResponse(BaseModel):
    """输入增强预览响应。"""
    original_text: str
    enhanced_text: str
    applied: bool = False
    reason: Optional[str] = None


class StoryAdjustmentPolishRequest(BaseModel):
    """故事选区润色请求（不影响正式会话状态）。"""
    story_id: str
    session_id: str
    segment_id: str
    selected_text: str = Field(..., min_length=1)
    before_context: Optional[str] = Field(default=None)
    after_context: Optional[str] = Field(default=None)
    preset_key: str = Field(..., min_length=1)
    preset_instruction: str = Field(..., min_length=1)
    custom_instruction: Optional[str] = Field(default=None)
    world_id: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    provider: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)


class StoryAdjustmentPolishResponse(BaseModel):
    """润色后的替换文本结果。"""
    story_id: str
    segment_id: str
    original_text: str
    polished_text: str
    model: str
    generation_time: float


class V2ContextItem(BaseModel):
    """检索上下文项（v2）。"""
    name: str
    type: str
    content: str
    score: float


class EntityStateQueryParams(BaseModel):
    """实体状态读取接口共享查询参数。"""

    entity_type: Optional[Literal["character"]] = Field(
        default=None,
        description="Optional entity type filter",
    )


class V2GenerateResponse(BaseModel):
    """故事生成 v2 响应。"""
    version: str = Field(default="v2")
    session_id: str
    thread_id: str
    output_text: str
    contexts: List[V2ContextItem] = Field(default_factory=list)
    activation_logs: List[Dict[str, Any]] = Field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    story_state_snapshot: Optional[Dict[str, Any]] = None
    story_memory: Optional[Dict[str, Any]] = None
    summary_memory_snapshot: Optional[Dict[str, Any]] = None
    runtime_state_snapshot: Optional[Dict[str, Any]] = None
    entity_state_snapshot: Optional[Dict[str, Any]] = None
    entity_state_updates: Optional[List[Dict[str, Any]]] = None
    world_update: Optional[Dict[str, Any]] = None
    creation_mode: Optional[str] = None
    consistency_check: Optional[Dict[str, Any]] = None
    model: str
    generation_time: float
    timestamp: datetime = Field(default_factory=datetime.now)
    # 选项模式下提取出的候选项。
    choices: List[str] = Field(default_factory=list)
    # 实际 token 统计；不可用时为 None（如流式路径或 provider 未返回）。
    tokens_used: Optional[Dict[str, int]] = None
    token_source: Optional[str] = None


# ------------------------------------------------------------------
# 会话管理 schema
# ------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    """显式创建故事会话请求。"""
    session_id: Optional[str] = Field(default=None)
    world_id: Optional[str] = Field(default=None)
    character_card_id: Optional[str] = Field(default=None)
    persona_id: Optional[str] = Field(default=None)


class CreateSessionResponse(BaseModel):
    """创建故事会话响应。"""
    session_id: str
    world_id: Optional[str] = None
    character_card_id: Optional[str] = None
    persona_id: Optional[str] = None
    first_message: Optional[str] = Field(
        default=None,
        description="Character's first message if the card defines one",
    )
    created_at: Optional[str] = None


class SessionInfoResponse(BaseModel):
    """故事会话元数据。"""
    session_id: str
    world_id: Optional[str] = None
    character_card_id: Optional[str] = None
    persona_id: Optional[str] = None
    first_message_sent: bool = False
    created_at: Optional[str] = None
    last_active_at: Optional[str] = None


# ------------------------------------------------------------------
# 回滚 / 重生成 schema
# ------------------------------------------------------------------

class RegenerateRequest(BaseModel):
    """删除最后助手消息并重生成的请求。"""
    story_id: Optional[str] = None
    persona_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(default=0.8, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=32000)
    authors_note: Optional[str] = None
    mode: Optional[Literal["narrative", "choices", "instruction"]] = "narrative"
    instruction: Optional[str] = None
    selected_context_entry_ids: List[str] = Field(default_factory=list)
    script_design_id: Optional[str] = None
    active_stage_id: Optional[str] = None
    active_event_id: Optional[str] = None
    follow_script_design: bool = False
    creation_mode: Literal["improv", "scripted"] = "improv"
    progress_intent: Literal["hold", "advance", "complete"] = "hold"
    runtime_state_id: Optional[str] = None
    allow_state_transition: bool = True
    principal_character_id: Optional[str] = None
    dialogue_mode: Optional[Literal["auto", "focused", "required"]] = Field(default="auto")
    dialogue_target: Optional[str] = None
    dialogue_intent: Optional[str] = None
    dialogue_style_hint: Optional[str] = None
    force_dialogue_round: bool = False
    focus_instruction: Optional[str] = None
    focus_label: Optional[str] = None


class DeleteLastMessageResponse(BaseModel):
    """删除最后一条助手消息后的响应。"""
    deleted: bool
    session_id: str
    detail: Optional[str] = None
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------
# 记忆更新日志 schema
# ------------------------------------------------------------------


class MemoryUpdateJournalItem(BaseModel):
    """持久化记忆更新日志项。"""
    event_id: str
    session_id: str
    operation_id: Optional[str] = None
    sequence: Optional[int] = None
    display_kind: Optional[str] = None
    world_id: Optional[str] = None
    memory_layer: str
    action: str
    source: str
    source_turn: Optional[int] = None
    memory_key: Optional[str] = None
    title: str
    reason: Optional[str] = None
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    status: str = "committed"
    committed_at: str


class MemoryUpdateJournalListResponse(BaseModel):
    """分页记忆更新日志列表。"""
    items: List[MemoryUpdateJournalItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class MemorySummaryStateResponse(BaseModel):
    """会话当前语义摘要状态。"""
    state: Literal["absent", "created", "reset", "recreated", "stale"] = "absent"
    current_summary: Optional[Dict[str, Any]] = None
    last_semantic_event: Optional[MemoryUpdateJournalItem] = None


class MemorySessionTimelineResponse(BaseModel):
    """会话维度记忆更新时间线。"""
    session_id: str
    world_id: Optional[str] = None
    items: List[MemoryUpdateJournalItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 100
    summary_state: MemorySummaryStateResponse = Field(default_factory=MemorySummaryStateResponse)


class StoryMemorySnapshotResponse(BaseModel):
    """统一故事记忆快照响应。"""
    session_id: str
    story_id: Optional[str] = None
    world_id: Optional[str] = None
    timeline_total: int = 0
    timeline_page: int = 1
    timeline_page_size: int = 50
    story_memory: Dict[str, Any] = Field(default_factory=dict)
