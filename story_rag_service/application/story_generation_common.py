"""
兼容层：导出故事生成应用层通用函数。

真实实现已拆分到 `application.story_generation.*` 子模块。
保留本模块用于兼容旧导入路径，避免一次性改动调用方。
"""

from application.story_generation import (
    archive_messages_outside_window,
    build_retrieval_query,
    format_recent_history_messages,
    load_world_config,
    retrieve_rag_context,
)

# 控制 import * 时可导出的公共符号。
__all__ = [
    # 仅暴露稳定兼容 API；内部实现细节由子模块维护。
    "build_retrieval_query",
    "retrieve_rag_context",
    "load_world_config",
    "format_recent_history_messages",
    "archive_messages_outside_window",
]
