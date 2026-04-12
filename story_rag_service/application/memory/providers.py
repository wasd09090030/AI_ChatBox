"""文件说明：后端应用层用例编排。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from models.roleplay import PersonaProfile
from models.story import StoryGenerationRequest

# 模块日志记录器，用于输出运行诊断信息。
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


def load_profile_snapshot(roleplay_manager, request: StoryGenerationRequest) -> Dict[str, Any]:
    """加载稳定的角色画像快照，不混入本轮 procedural controls。"""
    snapshot: Dict[str, Any] = {
        "character_card": None,
        "persona": _build_default_self_persona() if not request.persona_id else None,
        "story_state": None,
    }

    if not roleplay_manager:
        return snapshot

    try:
        if request.persona_id:
            persona = roleplay_manager.get_persona(request.persona_id)
            if persona is not None:
                snapshot["persona"] = persona.model_dump()
        else:
            snapshot["persona"] = _build_default_self_persona()

        if (request.story_state_mode or "off") != "off":
            state = roleplay_manager.get_story_state(request.session_id)
            if state is not None:
                snapshot["story_state"] = state.model_dump()
    except Exception as exc:
        logger.warning("Failed to load profile snapshot: %s", exc)
        return snapshot

    return snapshot


def build_dialogue_controls(request: StoryGenerationRequest) -> Dict[str, Any]:
    """构建 request-scoped 的对话控制项。"""
    return {
        "principal_character_id": getattr(request, "principal_character_id", None),
        "dialogue_mode": getattr(request, "dialogue_mode", "auto") or "auto",
        "dialogue_target": getattr(request, "dialogue_target", None),
        "dialogue_intent": getattr(request, "dialogue_intent", None),
        "dialogue_style_hint": getattr(request, "dialogue_style_hint", None),
        "force_dialogue_round": bool(getattr(request, "force_dialogue_round", False)),
    }


def load_script_guidance(script_design_app, request: StoryGenerationRequest) -> Dict[str, Any]:
    """加载当前剧本设计引导快照，用于程序化提示词注入。"""
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
