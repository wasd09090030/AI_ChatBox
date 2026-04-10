"""
Story Graph 节点逻辑集合。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from config import settings
from api import service_context as ctx
from models.roleplay import StoryStateUpdate
from models.story import StoryGenerationRequest

from .state import StoryGraphState


def _extract_clue_candidates(user_input: str) -> List[str]:
    """从用户输入中提取线索候选。

    提取策略：
    1. 优先提取引号/书名号中的短语；
    2. 若无命中，则按标点分词并筛选长度合适的词块；
    3. 去重后最多返回 3 条。
    """
    quoted = re.findall(r'“([^”]{2,24})”|"([^"]{2,24})"|《([^》]{2,24})》', user_input)
    merged_quoted = [part for group in quoted for part in group if part]
    if merged_quoted:
        return list(dict.fromkeys(merged_quoted[:3]))

    chunks = re.split(r"[，。！？、；,.!?;:\s]+", user_input)
    candidates = [chunk.strip() for chunk in chunks if 2 <= len(chunk.strip()) <= 24]
    return list(dict.fromkeys(candidates[:3]))


def _derive_state_update(existing_state: Any, user_input: str) -> StoryStateUpdate:
    """根据用户输入与已有状态构建新的 `StoryStateUpdate`。

    若旧状态字段缺失，会使用保守默认值兜底；线索列表会增量合并并保留最近窗口。
    """
    chapter = getattr(existing_state, "chapter", None) or "第一幕"
    objective = getattr(existing_state, "objective", None) or f"围绕“{user_input[:24]}”推进当前主线"
    conflict = getattr(existing_state, "conflict", None) or "推进目标时遭遇阻力与信息不对称"

    clues = list(getattr(existing_state, "clues", []) or [])
    for clue in _extract_clue_candidates(user_input):
        if clue not in clues:
            clues.append(clue)
    clues = clues[-8:]

    metadata = dict(getattr(existing_state, "metadata", {}) or {})
    metadata["last_user_input"] = user_input[:120]

    return StoryStateUpdate(
        chapter=chapter,
        objective=objective,
        conflict=conflict,
        clues=clues,
        metadata=metadata,
    )


async def prepare_request_node(state: StoryGraphState) -> Dict[str, Any]:
    """将图输入 payload 规范化为内部 `StoryGenerationRequest`。

    同时确保 session context 已创建，并把结果写回图状态。
    """
    payload = state["request_payload"]
    services = ctx.get_container()

    internal_request = StoryGenerationRequest(
        session_id=payload["session_id"],
        story_id=payload.get("story_id"),
        user_input=payload["user_input"],
        world_id=payload.get("world_id"),
        creation_mode=payload.get("creation_mode", "improv"),
        progress_intent=payload.get("progress_intent", "hold"),
        runtime_state_id=payload.get("runtime_state_id"),
        allow_state_transition=bool(payload.get("allow_state_transition", True)),
        model=payload.get("model"),
        provider=payload.get("provider"),
        base_url=payload.get("base_url"),
        temperature=payload.get("temperature"),
        max_tokens=payload.get("max_tokens"),
        use_rag=payload.get("use_rag", True),
        top_k=payload.get("top_k"),
        style=payload.get("style"),
        language=payload.get("language", "zh-CN"),
        character_card_id=payload.get("character_card_id"),
        persona_id=payload.get("persona_id"),
        story_state_mode=payload.get("story_state_mode"),
        authors_note=payload.get("authors_note"),
        mode=payload.get("mode", "narrative"),
        instruction=payload.get("instruction"),
        selected_context_entry_ids=payload.get("selected_context_entry_ids") or [],
        rag_scope_entry_ids=payload.get("rag_scope_entry_ids") or [],
        script_design_id=payload.get("script_design_id"),
        active_stage_id=payload.get("active_stage_id"),
        active_event_id=payload.get("active_event_id"),
        follow_script_design=bool(payload.get("follow_script_design", False)),
        principal_character_id=payload.get("principal_character_id"),
        dialogue_mode=payload.get("dialogue_mode") or "auto",
        dialogue_target=payload.get("dialogue_target"),
        dialogue_intent=payload.get("dialogue_intent"),
        dialogue_style_hint=payload.get("dialogue_style_hint"),
        force_dialogue_round=bool(payload.get("force_dialogue_round", False)),
        focus_instruction=payload.get("focus_instruction"),
        focus_label=payload.get("focus_label"),
        enhance_input=bool(payload.get("enhance_input", False)),
        memory_operation_id=payload.get("memory_operation_id"),
        memory_operation_sequence_start=int(payload.get("memory_operation_sequence_start") or 1),
    )

    # 统一在图入口获取/创建会话上下文，后续节点直接复用。
    context = services.session_manager.get_or_create_session(internal_request.session_id)
    internal_request.context = context
    return {"internal_request": internal_request}


async def update_story_state_node(state: StoryGraphState) -> Dict[str, Any]:
    """按 `story_state_mode` 更新剧情状态快照。

    `off` 模式不做任何更新；`light` 模式会压缩线索数量以控制状态体积。
    """
    internal_request = state["internal_request"]
    services = ctx.get_container()

    if not settings.rp_story_state_enabled:
        return {}

    story_state_mode = (internal_request.story_state_mode or "off").lower()
    if story_state_mode == "off":
        return {}

    existing_state = services.roleplay_manager.get_story_state(internal_request.session_id)
    update_payload = _derive_state_update(existing_state, internal_request.user_input)
    if story_state_mode == "light" and update_payload.clues:
        update_payload.clues = update_payload.clues[-4:]

    updated_state = services.roleplay_manager.upsert_story_state(
        internal_request.session_id,
        update_payload,
    )
    return {"story_state_snapshot": updated_state.model_dump()}


async def generate_story_node(state: StoryGraphState) -> Dict[str, Any]:
    """调用 StoryGenerator 执行核心生成。"""
    internal_request = state["internal_request"]
    services = ctx.get_container()
    user_id = state.get("user_id")
    response = await services.story_generator.generate_story(internal_request, user_id=user_id)
    return {"internal_response": response}


async def persist_session_node(state: StoryGraphState) -> Dict[str, Any]:
    """将生成后的 `updated_context` 回写到会话存储。"""
    internal_request = state["internal_request"]
    internal_response = state["internal_response"]
    services = ctx.get_container()
    services.session_manager.update_session(internal_request.session_id, internal_response.updated_context)
    return {}


async def build_v2_response_node(state: StoryGraphState) -> Dict[str, Any]:
    """将内部响应映射为 v2 API 响应结构。

    该节点负责：
    1. 按调试开关裁剪 activation_logs 与 story_state_snapshot；
    2. 解析 choices 模式文本中的 `[A]/[B]/[C]` 选项；
    3. 组装统一的 v2 响应字段。
    """
    internal_response = state["internal_response"]
    thread_id = state["thread_id"]
    debug_payload_enabled = settings.rp_debug_payload_enabled
    story_state_snapshot = state.get("story_state_snapshot") if debug_payload_enabled else None

    # 调试关闭时不向前端暴露调试链路细节。
    activation_logs = list(internal_response.activation_logs) if debug_payload_enabled else []
    internal_request = state["internal_request"]
    if debug_payload_enabled and getattr(internal_request, "principal_character_id", None):
        activation_logs.append(
            {
                "source": "dialogue_control",
                "event": "applied",
                "principal_character_id": internal_request.principal_character_id,
                "dialogue_mode": getattr(internal_request, "dialogue_mode", "auto"),
                "force_dialogue_round": bool(getattr(internal_request, "force_dialogue_round", False)),
            }
        )
    if debug_payload_enabled and getattr(internal_request, "script_design_id", None):
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
    if debug_payload_enabled and story_state_snapshot is not None:
        activation_logs.append(
            {
                "source": "story_state",
                "event": "updated",
                "chapter": story_state_snapshot.get("chapter"),
                "objective": story_state_snapshot.get("objective"),
                "clues_count": len(story_state_snapshot.get("clues") or []),
            }
        )

    raw_text = internal_response.generated_text
    choices: list = []
    # 与流式端保持一致：允许在最终文本中内嵌 [A]/[B]/[C] 候选行。
    choices_matches = re.findall(r"\[([ABC])\]\s*(.+)", raw_text)
    if choices_matches:
        choices = [text.strip() for _, text in choices_matches]
        raw_text = re.sub(r"\n?\[([ABC])\]\s*.+", "", raw_text).rstrip()

    contexts = [
        {
            "name": item.entry_name,
            "type": item.entry_type,
            "content": item.content,
            "score": item.relevance_score,
        }
        for item in internal_response.retrieved_contexts
    ]

    v2_response = {
        "session_id": internal_response.session_id,
        "thread_id": thread_id,
        "output_text": raw_text,
        "contexts": contexts,
        "activation_logs": activation_logs,
        "memory_updates": list(internal_response.memory_updates or []),
        "story_state_snapshot": story_state_snapshot,
        "story_memory": internal_response.story_memory,
        "summary_memory_snapshot": (
            internal_response.summary_memory_snapshot if debug_payload_enabled else None
        ),
        "runtime_state_snapshot": internal_response.runtime_state_snapshot,
        "entity_state_snapshot": internal_response.entity_state_snapshot,
        "entity_state_updates": internal_response.entity_state_updates,
        "world_update": internal_response.world_update,
        "creation_mode": internal_response.creation_mode,
        "consistency_check": internal_response.consistency_check,
        "model": internal_response.model_used,
        "generation_time": internal_response.generation_time,
        "choices": choices,
        "tokens_used": internal_response.tokens_used,
        "token_source": internal_response.token_source,
    }
    return {"v2_response": v2_response}
