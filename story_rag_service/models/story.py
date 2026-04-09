"""故事生成相关模型。"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class Message(BaseModel):
    """对话消息。"""
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)


class StoryContext(BaseModel):
    """用于生成的故事上下文。"""
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[Message] = Field(default_factory=list, description="Conversation history")
    world_state: Dict[str, Any] = Field(default_factory=dict, description="Current world state")
    active_characters: List[str] = Field(default_factory=list, description="Currently active characters")
    current_location: Optional[str] = None
    current_time: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryGenerationRequest(BaseModel):
    """故事生成请求。"""
    session_id: str = Field(..., description="Session identifier")
    story_id: Optional[str] = Field(default=None, description="Story ID bound to this generation round")
    user_input: str = Field(..., description="User's input/action")
    world_id: Optional[str] = Field(default=None, description="World ID to generate story in")
    context: Optional[StoryContext] = None
    
    # 生成参数
    model: Optional[str] = None
    provider: Optional[str] = None  # AI provider key (deepseek / qwen / openai / anthropic / gemini)
    base_url: Optional[str] = Field(
        default=None,
        description="Provider base URL override (highest priority; optional)",
    )
    temperature: Optional[float] = Field(default=0.8, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=32000)
    
    # 检索增强参数
    use_rag: bool = Field(default=True, description="Whether to use RAG for context")
    top_k: Optional[int] = Field(default=5, description="Number of relevant entries to retrieve")
    
    # 故事参数
    style: Optional[str] = Field(default="narrative", description="Writing style")
    language: str = Field(default="zh-CN", description="Response language")
    creation_mode: Literal["improv", "scripted"] = Field(
        default="improv",
        description="Story creation mode: improv or scripted",
    )
    progress_intent: Literal["hold", "advance", "complete"] = Field(
        default="hold",
        description="Whether the round only describes, advances, or completes the current scripted step",
    )
    runtime_state_id: Optional[str] = Field(
        default=None,
        description="Runtime state identifier for strict script mode",
    )
    allow_state_transition: bool = Field(
        default=True,
        description="Whether scripted mode may persist runtime state transition after generation",
    )
    rag_scope_entry_ids: List[str] = Field(
        default_factory=list,
        description="Internal filtered lorebook entry IDs for this round",
    )

    # 角色扮演扩展（向后兼容保留字段）
    character_card_id: Optional[str] = Field(default=None, description="Bound character card ID for roleplay")
    persona_id: Optional[str] = Field(default=None, description="Bound user persona ID for roleplay")
    story_state_mode: Optional[str] = Field(
        default=None,
        description="Story state strategy: off|light|strict (reserved for RP pipeline)",
    )

    # 借鉴 SillyTavern 的故事控制字段
    authors_note: Optional[str] = Field(default=None, description="Author's Note text injected near recent messages")
    mode: Optional[str] = Field(default="narrative", description="Generation mode: narrative|choices|instruction")
    instruction: Optional[str] = Field(default=None, description="Forced plot instruction when mode='instruction'")
    selected_context_entry_ids: List[str] = Field(
        default_factory=list,
        description="Explicit lorebook entry IDs selected by the user for this round",
    )
    script_design_id: Optional[str] = Field(
        default=None,
        description="Bound script design ID for this story round",
    )
    active_stage_id: Optional[str] = Field(
        default=None,
        description="Active script stage ID for this round",
    )
    active_event_id: Optional[str] = Field(
        default=None,
        description="Active script event ID for this round",
    )
    follow_script_design: bool = Field(
        default=False,
        description="Whether generation should follow the selected script design guidance",
    )
    principal_character_id: Optional[str] = Field(
        default=None,
        description="Lorebook 中被提升为本轮关键交流对象的角色条目 ID",
    )
    dialogue_mode: Optional[str] = Field(
        default="auto",
        description="关键角色交流模式：auto|focused|required",
    )
    dialogue_target: Optional[str] = Field(
        default=None,
        description="本轮对白面向的对象",
    )
    dialogue_intent: Optional[str] = Field(
        default=None,
        description="本轮对白目的",
    )
    dialogue_style_hint: Optional[str] = Field(
        default=None,
        description="本轮对白风格附加提示",
    )
    force_dialogue_round: bool = Field(
        default=False,
        description="是否强制本轮出现关键角色对白",
    )
    focus_instruction: Optional[str] = Field(
        default=None,
        description="Round-specific focus instruction chosen by the user",
    )
    focus_label: Optional[str] = Field(
        default=None,
        description="Display label for the round-specific focus instruction",
    )
    enhance_input: bool = Field(
        default=False,
        description="Whether to enhance short user input before main generation",
    )
    memory_operation_id: Optional[str] = Field(
        default=None,
        description="Internal operation group identifier for memory update chains",
    )
    memory_operation_sequence_start: int = Field(
        default=1,
        description="Internal sequence start for generated memory update events",
    )


class RetrievedContext(BaseModel):
    """从 lorebook 检索得到的上下文。"""
    entry_name: str
    entry_type: str
    content: str
    relevance_score: float


class StoryGenerationResponse(BaseModel):
    """故事生成响应。"""
    session_id: str
    user_input: str  # 用户输入
    generated_text: str  # AI 生成的文本
    response: Optional[str] = None  # 向后兼容的别名，会在序列化时自动填充
    retrieved_contexts: List[RetrievedContext] = Field(default_factory=list)
    updated_context: Optional[StoryContext] = None
    activation_logs: List[Dict[str, Any]] = Field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    story_state_snapshot: Optional[Dict[str, Any]] = None
    summary_memory_snapshot: Optional[Dict[str, Any]] = None
    runtime_state_snapshot: Optional[Dict[str, Any]] = None
    entity_state_snapshot: Optional[Dict[str, Any]] = None
    entity_state_updates: Optional[List[Dict[str, Any]]] = None
    world_update: Optional[Dict[str, Any]] = None
    creation_mode: Optional[str] = None
    consistency_check: Optional[Dict[str, Any]] = None
    
    # 元信息
    model_used: str = Field(alias="model_used")
    # 使用统计中记录的真实 token 数。
    # 不可用时为 None（如流式路径或 provider 未返回 usage）。
    tokens_used: Optional[Dict[str, int]] = None
    # 统计来源：provider_usage | estimated
    token_source: Optional[str] = None
    generation_time: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def model_post_init(self, __context):
        """初始化后自动设置 response 为 generated_text 的值"""
        if self.response is None:
            self.response = self.generated_text
    
    model_config = {
        "protected_namespaces": (),  # 允许 model_ 前缀的字段
        "populate_by_name": True
    }
