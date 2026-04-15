"""兼容层：导出故事生成应用层通用函数。

背景：历史代码大量依赖 `application.story_generation_common` 导入路径。
现已将真实实现拆分到 `application.story_generation.*` 子模块，
本文件仅作为“稳定转发层”，避免迁移期出现大规模连锁改动。
"""

from application.story_generation import (
    archive_messages_outside_window,
    build_retrieval_query,
    format_recent_history_messages,
    load_world_config,
    retrieve_rag_context,
)

# 控制 import * 时可导出的公共符号（仅暴露稳定兼容 API）。
__all__ = [
    # 内部实现细节由 `application.story_generation.*` 维护。
    "build_retrieval_query",
    "retrieve_rag_context",
    "load_world_config",
    "format_recent_history_messages",
    "archive_messages_outside_window",
]
