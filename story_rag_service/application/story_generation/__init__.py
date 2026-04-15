"""application.story_generation 包导出入口。

聚合故事生成应用层的核心能力：
- 检索查询与 RAG 召回编排；
- 短期窗口历史格式化与长期归档；
- 世界配置读取与风格注入。
"""

from .history_window import archive_messages_outside_window, format_recent_history_messages
from .retrieval import build_retrieval_query, retrieve_rag_context
from .world_config import load_world_config

# 控制 import * 时可导出的公共符号（面向服务编排层稳定 API）。
__all__ = [
    # 对外稳定 API，供服务编排层统一导入。
    "build_retrieval_query",
    "retrieve_rag_context",
    "load_world_config",
    "format_recent_history_messages",
    "archive_messages_outside_window",
]
