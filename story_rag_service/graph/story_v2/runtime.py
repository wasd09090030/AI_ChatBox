"""
Story Graph 运行时与生命周期管理。
"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from config import settings

from .nodes import (
    build_v2_response_node,
    generate_story_node,
    persist_session_node,
    prepare_request_node,
    update_story_state_node,
)
from .state import StoryGraphState

logger = logging.getLogger(__name__)
_story_graph = None
_async_checkpointer_context = None


def create_story_graph():
    """兼容保留：提示调用异步创建入口。"""
    raise RuntimeError("Use 'await get_story_graph()' for async initialization")


async def _create_checkpointer_async():
    """根据配置创建 checkpointer，失败时自动回退内存模式。

    支持后端：
    1. sqlite: 使用 AsyncSqliteSaver 持久化线程状态；
    2. memory: 使用 InMemorySaver（进程内临时状态）。
    """
    backend = (settings.langgraph_checkpoint_backend or "memory").lower()

    if backend == "sqlite":
        try:
            sqlite_module = importlib.import_module("langgraph.checkpoint.sqlite.aio")
            async_sqlite_saver = getattr(sqlite_module, "AsyncSqliteSaver")

            sqlite_path = settings.langgraph_checkpoint_sqlite_path
            sqlite_dir = os.path.dirname(sqlite_path)
            if sqlite_dir:
                os.makedirs(sqlite_dir, exist_ok=True)

            global _async_checkpointer_context
            # 保存 context 引用，便于 close_story_graph 时正确退出。
            _async_checkpointer_context = async_sqlite_saver.from_conn_string(sqlite_path)
            saver = await _async_checkpointer_context.__aenter__()

            logger.info("Using LangGraph SQLite checkpointer: %s", sqlite_path)
            return saver
        except Exception as exc:
            logger.warning("Failed to initialize SQLite checkpointer, fallback to InMemorySaver: %s", exc)

    logger.info("Using LangGraph InMemorySaver checkpointer")
    return InMemorySaver()


async def create_story_graph_async():
    """创建并编译 Story Graph。

    图执行顺序固定为：
    prepare_request -> update_story_state -> generate_story -> persist_session -> build_response。
    """
    checkpointer = await _create_checkpointer_async()
    graph = StateGraph(StoryGraphState)

    graph.add_node("prepare_request", prepare_request_node)
    graph.add_node("update_story_state", update_story_state_node)
    graph.add_node("generate_story", generate_story_node)
    graph.add_node("persist_session", persist_session_node)
    graph.add_node("build_response", build_v2_response_node)

    graph.add_edge(START, "prepare_request")
    graph.add_edge("prepare_request", "update_story_state")
    graph.add_edge("update_story_state", "generate_story")
    graph.add_edge("generate_story", "persist_session")
    graph.add_edge("persist_session", "build_response")
    graph.add_edge("build_response", END)
    return graph.compile(checkpointer=checkpointer)


async def get_story_graph():
    """懒加载并缓存图实例。

    进程生命周期内复用同一编译图，避免重复构图开销。
    """
    global _story_graph
    if _story_graph is None:
        _story_graph = await create_story_graph_async()
    return _story_graph


async def close_story_graph():
    """关闭异步 checkpointer 并清理图实例缓存。

    主要用于应用关闭或测试清理阶段，避免 sqlite 连接上下文泄漏。
    """
    global _story_graph, _async_checkpointer_context
    if _async_checkpointer_context is not None:
        await _async_checkpointer_context.__aexit__(None, None, None)
        _async_checkpointer_context = None
    _story_graph = None


async def run_story_graph(state: StoryGraphState):
    """执行 Story Graph 并返回最终状态。

    使用 `thread_id` 作为 LangGraph configurable key，以隔离会话线程状态。
    """
    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}
    graph = await get_story_graph()
    return await graph.ainvoke(state, config)
