"""
Story Graph 运行时与生命周期管理。
"""

from __future__ import annotations

import logging
from typing import Any

from bootstrap.config_resolver import resolve_story_graph_runtime_config

from .builder import compile_story_graph
from .checkpointer import create_story_graph_checkpointer
from .state import StoryGraphState

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)
# 缓存已编译的 Story Graph 单例，避免重复构图。
_story_graph = None
# 保存异步 checkpointer 上下文，便于关闭阶段显式释放连接。
_async_checkpointer_context = None


def create_story_graph():
    """兼容保留的同步入口。

    当前 checkpointer 初始化依赖异步流程，调用方应改用 `await get_story_graph()`。
    """
    raise RuntimeError("Use 'await get_story_graph()' for async initialization")


async def _create_checkpointer_async():
    """根据配置创建 checkpointer，失败时自动回退内存模式。

    支持后端：
    1. sqlite: 使用 AsyncSqliteSaver 持久化线程状态；
    2. memory: 使用 InMemorySaver（进程内临时状态）。
    """
    global _async_checkpointer_context
    runtime_config = resolve_story_graph_runtime_config()
    saver, context = await create_story_graph_checkpointer(runtime_config)
    _async_checkpointer_context = context
    return saver


async def create_story_graph_async():
    """创建并编译 Story Graph。

    图执行顺序固定为：
    prepare_request -> update_story_state -> generate_story -> persist_session -> build_response。
    """
    checkpointer = await _create_checkpointer_async()
    return compile_story_graph(checkpointer=checkpointer)


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
