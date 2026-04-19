"""故事生成请求构建器。

把 API schema 或 graph payload 与会话上下文归一化为 StoryGenerationRequest，
避免 HTTP 路由层和 graph 节点重复拼装内部请求对象。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Union

from api.v2.schemas import V2GenerateRequest, V2InputEnhancementPreviewRequest
from models.story import StoryGenerationRequest


StoryGenerationApiRequest = Union[V2GenerateRequest, V2InputEnhancementPreviewRequest]


@dataclass(frozen=True)
class StoryGenerationPayloadAdapter:
    """把 dict payload 适配为 attribute 风格对象。"""

    payload: Mapping[str, Any]

    def __getattr__(self, item: str) -> Any:
        try:
            return self.payload[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def build_story_generation_request(
    *,
    request: StoryGenerationApiRequest,
    session_context: Any,
    session_id: Optional[str] = None,
    enhance_input: Optional[bool] = None,
    memory_operation_id: Optional[str] = None,
    memory_operation_sequence_start: int = 1,
) -> StoryGenerationRequest:
    """根据 API 请求与会话上下文构建内部故事生成请求。"""
    payload = {
        "session_id": session_id or request.session_id,
        "story_id": request.story_id,
        "user_input": request.user_input,
        "world_id": request.world_id,
        "creation_mode": request.creation_mode,
        "progress_intent": request.progress_intent,
        "runtime_state_id": request.runtime_state_id,
        "allow_state_transition": request.allow_state_transition,
        "context": session_context,
        "model": request.model,
        "provider": request.provider,
        "base_url": request.base_url,
        "temperature": request.temperature,
        "character_card_id": getattr(request, "character_card_id", None),
        "persona_id": request.persona_id,
        "selected_context_entry_ids": list(getattr(request, "selected_context_entry_ids", []) or []),
        "rag_scope_entry_ids": [],
        "script_design_id": getattr(request, "script_design_id", None),
        "active_stage_id": getattr(request, "active_stage_id", None),
        "active_event_id": getattr(request, "active_event_id", None),
        "follow_script_design": bool(getattr(request, "follow_script_design", False)),
        "principal_character_id": getattr(request, "principal_character_id", None),
        "dialogue_mode": getattr(request, "dialogue_mode", None),
        "dialogue_target": getattr(request, "dialogue_target", None),
        "dialogue_intent": getattr(request, "dialogue_intent", None),
        "dialogue_style_hint": getattr(request, "dialogue_style_hint", None),
        "force_dialogue_round": bool(getattr(request, "force_dialogue_round", False)),
        "focus_instruction": getattr(request, "focus_instruction", None),
        "focus_label": getattr(request, "focus_label", None),
    }

    optional_field_names = (
        "max_tokens",
        "use_rag",
        "top_k",
        "style",
        "language",
        "story_state_mode",
        "authors_note",
        "mode",
        "instruction",
    )
    for field_name in optional_field_names:
        if hasattr(request, field_name):
            payload[field_name] = getattr(request, field_name)

    payload["enhance_input"] = (
        getattr(request, "enhance_input", False) if enhance_input is None else enhance_input
    )
    if memory_operation_id is not None:
        payload["memory_operation_id"] = memory_operation_id
        payload["memory_operation_sequence_start"] = memory_operation_sequence_start

    return StoryGenerationRequest(**payload)


def build_story_generation_request_from_payload(
    *,
    payload: Mapping[str, Any],
    session_context: Any,
) -> StoryGenerationRequest:
    """根据 graph payload 与会话上下文构建内部故事生成请求。"""
    adapted_request = StoryGenerationPayloadAdapter(payload)
    return build_story_generation_request(
        request=adapted_request,
        session_context=session_context,
        session_id=str(payload["session_id"]),
        enhance_input=bool(payload.get("enhance_input", False)),
        memory_operation_id=payload.get("memory_operation_id"),
        memory_operation_sequence_start=int(payload.get("memory_operation_sequence_start") or 1),
    )
