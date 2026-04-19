"""Story Graph 编译辅助。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    build_v2_response_node,
    generate_story_node,
    persist_session_node,
    prepare_request_node,
    update_story_state_node,
)
from .state import StoryGraphState


def compile_story_graph(*, checkpointer):
    """创建并编译 Story Graph。"""
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
