"""application.story_generation 包导出入口。

聚合故事生成应用层的稳定能力边界，供 route / graph / bootstrap 复用：
- 请求构建、Session Context 读取与回写；
- Story Graph facade / runner；
- 检索、历史窗口、世界配置、剧情状态、响应映射；
- 生成观测与非流式执行用例。
"""

from __future__ import annotations

from typing import Any

from .history_window import archive_messages_outside_window, format_recent_history_messages
from .observability import (
    build_observability_counters,
    record_generation_failure,
    record_generation_success,
    resolve_token_usage,
)
from .execution import execute_story_generation
from .request_builder import build_story_generation_request, build_story_generation_request_from_payload
from .response_builder import build_story_graph_v2_response
from .retrieval import build_retrieval_query, retrieve_rag_context
from .session_context import load_or_create_story_session_context, persist_story_session_context
from .story_state import derive_story_state_update, extract_clue_candidates, update_story_state_snapshot
from .world_config import load_world_config


def build_story_graph_request_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """延迟导入 graph facade，避免 application/story_generation 包级循环依赖。"""
    from .graph_facade import build_story_graph_request_payload as _impl

    return _impl(*args, **kwargs)


async def execute_story_graph_generation(*args: Any, **kwargs: Any) -> Any:
    """延迟导入 graph facade，避免 application/story_generation 包级循环依赖。"""
    from .graph_facade import execute_story_graph_generation as _impl

    return await _impl(*args, **kwargs)


async def run_story_graph_state(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """延迟导入 graph runner，避免 application/story_generation 包级循环依赖。"""
    from .graph_runner import run_story_graph_state as _impl

    return await _impl(*args, **kwargs)


async def shutdown_story_graph_runtime(*args: Any, **kwargs: Any) -> None:
    """延迟导入 graph runner，避免 application/story_generation 包级循环依赖。"""
    from .graph_runner import shutdown_story_graph_runtime as _impl

    return await _impl(*args, **kwargs)

# 控制 import * 时可导出的公共符号（面向服务编排层稳定 API）。
__all__ = [
    # 对外稳定 API，供服务编排层统一导入。
    "build_retrieval_query",
    "retrieve_rag_context",
    "load_world_config",
    "build_story_graph_request_payload",
    "format_recent_history_messages",
    "archive_messages_outside_window",
    "build_observability_counters",
    "build_story_generation_request",
    "build_story_generation_request_from_payload",
    "build_story_graph_v2_response",
    "execute_story_generation",
    "derive_story_state_update",
    "execute_story_graph_generation",
    "extract_clue_candidates",
    "load_or_create_story_session_context",
    "persist_story_session_context",
    "record_generation_failure",
    "record_generation_success",
    "resolve_token_usage",
    "run_story_graph_state",
    "shutdown_story_graph_runtime",
    "update_story_state_snapshot",
]
