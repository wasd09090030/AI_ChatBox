"""故事生成响应构建辅助。"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _extract_choices_and_clean_text(raw_text: str) -> tuple[List[str], str]:
    """解析 choices 模式内嵌候选，并返回清洗后的正文。"""
    choices_matches = re.findall(r"\[([ABC])\]\s*(.+)", raw_text)
    if not choices_matches:
        return [], raw_text
    choices = [text.strip() for _, text in choices_matches]
    cleaned_text = re.sub(r"\n?\[([ABC])\]\s*.+", "", raw_text).rstrip()
    return choices, cleaned_text


def build_graph_activation_logs(
    *,
    internal_response: Any,
    internal_request: Any,
    story_state_snapshot: Optional[Dict[str, Any]],
    debug_payload_enabled: bool,
) -> List[Dict[str, Any]]:
    """构建 graph 返回给 v2 响应的 activation logs。"""
    if not debug_payload_enabled:
        return []

    activation_logs = list(getattr(internal_response, "activation_logs", None) or [])
    if getattr(internal_request, "principal_character_id", None):
        activation_logs.append(
            {
                "source": "dialogue_control",
                "event": "applied",
                "principal_character_id": internal_request.principal_character_id,
                "dialogue_mode": getattr(internal_request, "dialogue_mode", "auto"),
                "force_dialogue_round": bool(getattr(internal_request, "force_dialogue_round", False)),
            }
        )
    if getattr(internal_request, "script_design_id", None):
        activation_logs.append(
            {
                "source": "script_design",
                "event": "requested",
                "script_design_id": internal_request.script_design_id,
                "active_stage_id": getattr(internal_request, "active_stage_id", None),
                "active_event_id": getattr(internal_request, "active_event_id", None),
                "follow_script_design": bool(getattr(internal_request, "follow_script_design", False)),
            }
        )
    if story_state_snapshot is not None:
        activation_logs.append(
            {
                "source": "story_state",
                "event": "updated",
                "chapter": story_state_snapshot.get("chapter"),
                "objective": story_state_snapshot.get("objective"),
                "clues_count": len(story_state_snapshot.get("clues") or []),
            }
        )
    return activation_logs


def build_story_graph_v2_response(
    *,
    internal_response: Any,
    internal_request: Any,
    thread_id: str,
    story_state_snapshot: Optional[Dict[str, Any]],
    debug_payload_enabled: bool,
) -> Dict[str, Any]:
    """将内部响应映射为 v2 API 响应结构。"""
    raw_text = str(getattr(internal_response, "generated_text", "") or "")
    choices, cleaned_text = _extract_choices_and_clean_text(raw_text)
    activation_logs = build_graph_activation_logs(
        internal_response=internal_response,
        internal_request=internal_request,
        story_state_snapshot=story_state_snapshot,
        debug_payload_enabled=debug_payload_enabled,
    )

    contexts = [
        {
            "name": item.entry_name,
            "type": item.entry_type,
            "content": item.content,
            "score": item.relevance_score,
        }
        for item in list(getattr(internal_response, "retrieved_contexts", None) or [])
    ]

    return {
        "session_id": internal_response.session_id,
        "thread_id": thread_id,
        "output_text": cleaned_text,
        "contexts": contexts,
        "activation_logs": activation_logs,
        "memory_updates": list(getattr(internal_response, "memory_updates", None) or []),
        "story_state_snapshot": story_state_snapshot,
        "story_memory": getattr(internal_response, "story_memory", None),
        "summary_memory_snapshot": (
            getattr(internal_response, "summary_memory_snapshot", None) if debug_payload_enabled else None
        ),
        "runtime_state_snapshot": getattr(internal_response, "runtime_state_snapshot", None),
        "entity_state_snapshot": getattr(internal_response, "entity_state_snapshot", None),
        "entity_state_updates": getattr(internal_response, "entity_state_updates", None),
        "world_update": getattr(internal_response, "world_update", None),
        "creation_mode": getattr(internal_response, "creation_mode", None),
        "consistency_check": getattr(internal_response, "consistency_check", None),
        "model": getattr(internal_response, "model_used", None),
        "generation_time": getattr(internal_response, "generation_time", 0.0),
        "choices": choices,
        "tokens_used": getattr(internal_response, "tokens_used", None),
        "token_source": getattr(internal_response, "token_source", None),
    }
