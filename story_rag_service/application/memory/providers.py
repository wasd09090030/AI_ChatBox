"""记忆提供器集合。

面向 MemoryOrchestrator 提供“可复用的数据装配函数”，负责把请求中的控制参数
与持久化资源（persona、story_state、script_design）转换成稳定快照。

边界说明：
1) 本模块只负责读取与归一化，不做持久化写入；
2) 返回结果以“可直接注入 MemoryBundle”为目标，不掺杂页面 UI 状态。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from models.roleplay import PersonaProfile
from models.story import StoryGenerationRequest

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


def _build_default_self_persona() -> Dict[str, Any]:
    """构建默认主角画像。

    当请求未指定 persona_id 时，系统使用“你自己”作为主角兜底，避免角色层为空。
    """
    return PersonaProfile(
        name="你自己",
        description="默认主角就是当前输入这段故事指令的用户本人。除非用户明确补充，否则不要擅自设定主角的固定外貌、性别、年龄、身份或详细背景。",
        title=None,
        traits=[],
        metadata={"source": "implicit_user_self"},
    ).model_dump()


def load_profile_snapshot(
    roleplay_manager,
    request: StoryGenerationRequest,
    *,
    owner_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """加载角色画像层快照。

    返回字段约定：
    - character_card: 角色卡（当前链路暂未启用，保留位）；
    - persona: 本轮主角画像，若未指定则回退“你自己”；
    - story_state: roleplay 侧长期状态（受 story_state_mode 控制）。
    """
    snapshot: Dict[str, Any] = {
        "character_card": None,
        "persona": _build_default_self_persona() if not request.persona_id else None,
        "story_state": None,
    }

    # 缺少 roleplay_manager 时直接返回兜底快照，保证调用方结构稳定。
    if not roleplay_manager:
        return snapshot

    try:
        # persona 的优先级：显式 persona_id > 默认“你自己”。
        if request.persona_id:
            persona = roleplay_manager.get_persona(
                request.persona_id,
                owner_user_id=owner_user_id,
            )
            if persona is not None:
                snapshot["persona"] = persona.model_dump()
        else:
            snapshot["persona"] = _build_default_self_persona()

        # 仅在 story_state_mode 开启时读取长期状态，避免无谓 I/O。
        if (request.story_state_mode or "off") != "off":
            state = roleplay_manager.get_story_state(
                request.session_id,
                owner_user_id=owner_user_id,
            )
            if state is not None:
                snapshot["story_state"] = state.model_dump()
    except Exception as exc:
        logger.warning("Failed to load profile snapshot: %s", exc)
        return snapshot

    return snapshot


def build_dialogue_controls(request: StoryGenerationRequest) -> Dict[str, Any]:
    """提取 request 级对白控制参数。

    这些字段属于 procedural controls：只影响当前轮生成，不写入长期画像快照。
    """
    return {
        "principal_character_id": getattr(request, "principal_character_id", None),
        "dialogue_mode": getattr(request, "dialogue_mode", "auto") or "auto",
        "dialogue_target": getattr(request, "dialogue_target", None),
        "dialogue_intent": getattr(request, "dialogue_intent", None),
        "dialogue_style_hint": getattr(request, "dialogue_style_hint", None),
        "force_dialogue_round": bool(getattr(request, "force_dialogue_round", False)),
    }


def load_script_guidance(
    script_design_app,
    request: StoryGenerationRequest,
    *,
    owner_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """读取并裁剪剧本引导快照。

    激活条件：request 同时提供 script_design_id 且 follow_script_design 为真。
    返回内容会被注入 procedural 层，供提示词构建器进行主线约束。
    """
    if not script_design_app:
        return {}

    script_design_id = getattr(request, "script_design_id", None)
    if not script_design_id or not bool(getattr(request, "follow_script_design", False)):
        return {}

    try:
        script_design = script_design_app.get_script_design(
            script_design_id,
            owner_user_id=owner_user_id,
        )
    except Exception as exc:
        logger.warning("Failed to load script design: %s", exc)
        return {}

    if script_design is None:
        return {}

    stage = None
    event = None
    active_stage_id = getattr(request, "active_stage_id", None)
    active_event_id = getattr(request, "active_event_id", None)

    # 阶段选择优先级：显式 active_stage_id > policy 首选 > 第一阶段。
    if active_stage_id:
        stage = next((item for item in script_design.stage_outlines if item.id == active_stage_id), None)
    if stage is None:
        preferred_stage_id = getattr(script_design.default_generation_policy, "preferred_stage_id", None)
        if preferred_stage_id:
            stage = next((item for item in script_design.stage_outlines if item.id == preferred_stage_id), None)
    if stage is None and script_design.stage_outlines:
        stage = script_design.stage_outlines[0]

    # 事件选择优先级：显式 active_event_id > 当前阶段 pending/active > 全局 pending/active > 首事件。
    if active_event_id:
        event = next((item for item in script_design.event_nodes if item.id == active_event_id), None)
    if event is None and stage is not None:
        stage_events = [item for item in script_design.event_nodes if item.stage_id == stage.id]
        pending_event = next((item for item in stage_events if item.status in {"pending", "active"}), None)
        event = pending_event or (stage_events[0] if stage_events else None)
    if event is None:
        pending_event = next((item for item in script_design.event_nodes if item.status in {"pending", "active"}), None)
        event = pending_event or (script_design.event_nodes[0] if script_design.event_nodes else None)

    # 仅返回未兑现 foreshadow，且优先高重要度，避免提示词上下文噪声过大。
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
