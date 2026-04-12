"""
故事上下文相关辅助函数。
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from models.roleplay import PersonaProfile
from models.story import Message, RetrievedContext, StoryGenerationRequest
import logging

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


def _build_default_self_persona() -> Dict[str, Any]:
    """在未显式选择 persona 时，默认将主角视为用户本人。"""
    return PersonaProfile(
        name="你自己",
        description="默认主角就是当前输入这段故事指令的用户本人。除非用户明确补充，否则不要擅自设定主角的固定外貌、性别、年龄、身份或详细背景。",
        title=None,
        traits=[],
        metadata={"source": "implicit_user_self"},
    ).model_dump()


def _resolve_context_score(context_item: Dict[str, Any]) -> float:
    """功能：解析并返回上下文 score。"""
    raw_score = context_item.get("relevance_score", context_item.get("score", 0.0))
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def load_roleplay_profile(roleplay_manager, request: StoryGenerationRequest) -> Dict[str, Any]:
    """根据请求中的角色绑定加载角色扮演画像。"""
    profile: Dict[str, Any] = {
        "story_state_mode": request.story_state_mode or "off",
        "character_card": None,
        "persona": _build_default_self_persona() if not request.persona_id else None,
        "story_state": None,
        "dialogue_controls": {
            "principal_character_id": getattr(request, "principal_character_id", None),
            "dialogue_mode": getattr(request, "dialogue_mode", "auto") or "auto",
            "dialogue_target": getattr(request, "dialogue_target", None),
            "dialogue_intent": getattr(request, "dialogue_intent", None),
            "dialogue_style_hint": getattr(request, "dialogue_style_hint", None),
            "force_dialogue_round": bool(getattr(request, "force_dialogue_round", False)),
        },
    }

    if not roleplay_manager:
        return profile

    try:
        if request.persona_id:
            persona = roleplay_manager.get_persona(request.persona_id)
            if persona is not None:
                profile["persona"] = persona.model_dump()
        else:
            profile["persona"] = _build_default_self_persona()

        if (request.story_state_mode or "off") != "off":
            state = roleplay_manager.get_story_state(request.session_id)
            if state is not None:
                profile["story_state"] = state.model_dump()
    except Exception as exc:
        logger.warning("Failed to load roleplay profile: %s", exc)
        return profile

    return profile


def load_script_design_context(script_design_app, request: StoryGenerationRequest) -> Dict[str, Any]:
    """加载当前剧本设计指导快照，用于注入提示词上下文。"""
    if not script_design_app:
        return {}

    script_design_id = getattr(request, "script_design_id", None)
    if not script_design_id or not bool(getattr(request, "follow_script_design", False)):
        return {}

    try:
        script_design = script_design_app.get_script_design(script_design_id)
    except Exception as exc:
        logger.warning("Failed to load script design: %s", exc)
        return {}

    if script_design is None:
        return {}

    stage = None
    event = None
    active_stage_id = getattr(request, "active_stage_id", None)
    active_event_id = getattr(request, "active_event_id", None)

    if active_stage_id:
        stage = next((item for item in script_design.stage_outlines if item.id == active_stage_id), None)
    if stage is None:
        preferred_stage_id = getattr(script_design.default_generation_policy, "preferred_stage_id", None)
        if preferred_stage_id:
            stage = next((item for item in script_design.stage_outlines if item.id == preferred_stage_id), None)
    if stage is None and script_design.stage_outlines:
        stage = script_design.stage_outlines[0]

    if active_event_id:
        event = next((item for item in script_design.event_nodes if item.id == active_event_id), None)
    if event is None and stage is not None:
        stage_events = [item for item in script_design.event_nodes if item.stage_id == stage.id]
        pending_event = next((item for item in stage_events if item.status in {"pending", "active"}), None)
        event = pending_event or (stage_events[0] if stage_events else None)
    if event is None:
        pending_event = next((item for item in script_design.event_nodes if item.status in {"pending", "active"}), None)
        event = pending_event or (script_design.event_nodes[0] if script_design.event_nodes else None)

    highlighted_foreshadows = [item for item in script_design.foreshadows if item.status != "paid_off"]
    highlighted_foreshadows.sort(key=lambda item: (item.importance != "high", item.title))

    return {
        "script_design_id": script_design.id,
        "title": script_design.title,
        "summary": script_design.summary,
        "logline": script_design.logline,
        "theme": script_design.theme,
        "core_conflict": script_design.core_conflict,
        "tone_style": script_design.tone_style,
        "follow_script_design": bool(getattr(request, "follow_script_design", False)),
        "active_stage": stage.model_dump() if stage is not None else None,
        "active_event": event.model_dump() if event is not None else None,
        "highlighted_foreshadows": [item.model_dump() for item in highlighted_foreshadows[:3]],
    }


def persist_message_to_db(database_path: str, session_id: str, role: str, content: str) -> None:
    """持久化单条会话消息到 story_session_messages。"""
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        INSERT OR IGNORE INTO story_session_messages
            (id, session_id, role, content, token_estimate, archived)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (str(uuid.uuid4()), session_id, role, content, len(content) // 4),
    )
    conn.commit()
    conn.close()


def format_conversation_history(messages: List[Message], max_history: int = 10) -> List[Any]:
    """将内部消息记录转换为 LLM 可读历史消息。"""
    recent_messages = messages[-max_history:] if len(messages) > max_history else messages
    formatted: List[Any] = []
    for msg in recent_messages:
        if msg.role == "user":
            formatted.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            formatted.append(AIMessage(content=msg.content))
    return formatted


def format_retrieved_contexts(
    retrieved_contexts: List[Dict[str, Any]],
    retrieved_history: List[Dict[str, Any]],
    history_name_template: str = "Turn {turn} - {role}",
) -> List[RetrievedContext]:
    """将 lorebook 命中与历史命中合并为统一响应结构。"""
    formatted_contexts = [
        RetrievedContext(
            entry_name=context_item["name"],
            entry_type=context_item["type"],
            content=context_item["content"],
            relevance_score=_resolve_context_score(context_item),
        )
        for context_item in retrieved_contexts
    ]

    for history_item in retrieved_history:
        formatted_contexts.append(
            RetrievedContext(
                entry_name=history_name_template.format(
                    turn=history_item["turn_number"],
                    role=history_item["role"],
                ),
                entry_type="conversation_history",
                content=history_item["content"],
                relevance_score=history_item["relevance_score"],
            )
        )
    return formatted_contexts
