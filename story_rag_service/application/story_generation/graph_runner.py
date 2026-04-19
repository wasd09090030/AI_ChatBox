"""Story Graph 运行器。

对 application 层暴露稳定的 graph 执行与关闭入口，隔离 `graph.story_v2.runtime`
中的 LangGraph 技术细节与生命周期管理。
"""

from __future__ import annotations

from typing import Any

from graph.story_v2.runtime import close_story_graph, run_story_graph
from graph.story_v2.state import StoryGraphState


async def run_story_graph_state(state: StoryGraphState) -> Any:
    """执行 Story Graph 并返回最终状态。"""
    return await run_story_graph(state)


async def shutdown_story_graph_runtime() -> None:
    """关闭 Story Graph 运行时资源。"""
    await close_story_graph()
