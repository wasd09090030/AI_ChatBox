"""
Story Graph 节点逻辑集合。
"""

from __future__ import annotations

from typing import Any, Dict

from application.story_generation.execution import execute_story_generation
from application.story_generation.request_builder import build_story_generation_request_from_payload
from application.story_generation.response_builder import build_story_graph_v2_response
from application.story_generation.session_context import (
    load_or_create_story_session_context,
    persist_story_session_context,
)
from application.story_generation.story_state import update_story_state_snapshot
from bootstrap.config_resolver import resolve_story_graph_feature_flags
from bootstrap.container import get_container

from .state import StoryGraphState


async def prepare_request_node(state: StoryGraphState) -> Dict[str, Any]:
    """将图输入 payload 规范化为内部 `StoryGenerationRequest`。

    同时确保 session context 已创建，并把结果写回图状态。
    """
    payload = state["request_payload"]
    services = get_container()

    context = load_or_create_story_session_context(
        session_store=services.session_manager,
        payload=payload,
    )
    internal_request = build_story_generation_request_from_payload(
        payload=payload,
        session_context=context,
    )
    return {"internal_request": internal_request}


async def update_story_state_node(state: StoryGraphState) -> Dict[str, Any]:
    """按 `story_state_mode` 更新剧情状态快照。

    `off` 模式不做任何更新；`light` 模式会压缩线索数量以控制状态体积。
    """
    internal_request = state["internal_request"]
    services = get_container()
    feature_flags = resolve_story_graph_feature_flags()
    story_state_snapshot = update_story_state_snapshot(
        roleplay_manager=services.roleplay_manager,
        session_id=internal_request.session_id,
        user_input=internal_request.user_input,
        story_state_mode=internal_request.story_state_mode,
        story_state_enabled=feature_flags.rp_story_state_enabled,
    )
    return {"story_state_snapshot": story_state_snapshot} if story_state_snapshot is not None else {}


async def generate_story_node(state: StoryGraphState) -> Dict[str, Any]:
    """调用 StoryGenerator 执行核心生成。"""
    internal_request = state["internal_request"]
    services = get_container()
    user_id = state.get("user_id")
    response = await execute_story_generation(
        executor=services.story_generator,
        request=internal_request,
        user_id=user_id,
    )
    return {"internal_response": response}


async def persist_session_node(state: StoryGraphState) -> Dict[str, Any]:
    """将生成后的 `updated_context` 回写到会话存储。"""
    internal_request = state["internal_request"]
    internal_response = state["internal_response"]
    services = get_container()
    persist_story_session_context(
        session_store=services.session_manager,
        session_id=internal_request.session_id,
        updated_context=internal_response.updated_context,
    )
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
    debug_payload_enabled = resolve_story_graph_feature_flags().rp_debug_payload_enabled
    story_state_snapshot = state.get("story_state_snapshot") if debug_payload_enabled else None
    internal_request = state["internal_request"]
    v2_response = build_story_graph_v2_response(
        internal_response=internal_response,
        internal_request=internal_request,
        thread_id=thread_id,
        story_state_snapshot=story_state_snapshot,
        debug_payload_enabled=debug_payload_enabled,
    )
    return {"v2_response": v2_response}
