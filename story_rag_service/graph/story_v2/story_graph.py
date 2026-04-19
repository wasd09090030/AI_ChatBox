"""
兼容层：导出 Story Graph 运行时与节点函数。

真实实现已拆分到 `graph.story_v2.runtime` 与 `graph.story_v2.nodes`。
新代码应优先依赖 `application.story_generation` 暴露的 facade / runner。
"""

from application.story_generation import (
    derive_story_state_update as _derive_state_update,
    extract_clue_candidates as _extract_clue_candidates,
)
from .nodes import (
    build_v2_response_node,
    generate_story_node,
    persist_session_node,
    prepare_request_node,
    update_story_state_node,
)
from .runtime import (
    close_story_graph,
    create_story_graph,
    create_story_graph_async,
    get_story_graph,
    run_story_graph,
)

# 控制 import * 时可导出的公共符号。
__all__ = [
    "_extract_clue_candidates",
    "_derive_state_update",
    "prepare_request_node",
    "update_story_state_node",
    "generate_story_node",
    "persist_session_node",
    "build_v2_response_node",
    "create_story_graph",
    "create_story_graph_async",
    "get_story_graph",
    "close_story_graph",
    "run_story_graph",
]
