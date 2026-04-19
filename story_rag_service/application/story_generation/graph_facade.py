"""故事生成 LangGraph facade。

把 graph 输入载荷组装与执行封装到 application 层，避免路由直接依赖
`graph.story_v2.run_story_graph(...)` 与底层 state 结构。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from api.v2.schemas import RegenerateRequest, V2GenerateRequest, V2GenerateResponse

from .graph_runner import run_story_graph_state


StoryGraphApiRequest = Union[V2GenerateRequest, RegenerateRequest]


def build_story_graph_request_payload(
    *,
    request: StoryGraphApiRequest,
    session_id: str,
    user_input: str,
    memory_operation_id: Optional[str] = None,
    memory_operation_sequence_start: int = 1,
) -> Dict[str, Any]:
    """根据 API 请求构建 Story Graph 输入 payload。"""
    payload: Dict[str, Any] = {
        "session_id": session_id,
        "story_id": getattr(request, "story_id", None),
        "user_input": user_input,
        "world_id": getattr(request, "world_id", None),
        "creation_mode": getattr(request, "creation_mode", "improv"),
        "progress_intent": getattr(request, "progress_intent", "hold"),
        "runtime_state_id": getattr(request, "runtime_state_id", None),
        "allow_state_transition": bool(getattr(request, "allow_state_transition", True)),
        "model": getattr(request, "model", None),
        "provider": getattr(request, "provider", None),
        "base_url": getattr(request, "base_url", None),
        "temperature": getattr(request, "temperature", None),
        "persona_id": getattr(request, "persona_id", None),
        "selected_context_entry_ids": list(getattr(request, "selected_context_entry_ids", []) or []),
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
        "character_card_id",
        "story_state_mode",
        "authors_note",
        "mode",
        "instruction",
        "enhance_input",
    )
    for field_name in optional_field_names:
        if hasattr(request, field_name):
            payload[field_name] = getattr(request, field_name)

    if memory_operation_id is not None:
        payload["memory_operation_id"] = memory_operation_id
        payload["memory_operation_sequence_start"] = memory_operation_sequence_start

    return payload


async def execute_story_graph_generation(
    *,
    request_payload: Dict[str, Any],
    thread_id: str,
    user_id: Optional[str],
) -> V2GenerateResponse:
    """执行 Story Graph 并返回标准 v2 响应。"""
    graph_state = await run_story_graph_state(
        {
            "request_payload": request_payload,
            "thread_id": thread_id,
            "user_id": user_id,
        }
    )
    return V2GenerateResponse(**graph_state["v2_response"])
