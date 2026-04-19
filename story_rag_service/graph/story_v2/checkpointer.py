"""Story Graph checkpointer 创建辅助。"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any, Optional, Tuple

from langgraph.checkpoint.memory import InMemorySaver

from bootstrap.config_resolver import StoryGraphRuntimeConfig

logger = logging.getLogger(__name__)


async def create_story_graph_checkpointer(
    runtime_config: StoryGraphRuntimeConfig,
) -> Tuple[Any, Optional[Any]]:
    """根据配置创建 checkpointer 与可选上下文句柄。"""
    backend = (runtime_config.checkpoint_backend or "memory").lower()

    if backend == "sqlite":
        try:
            sqlite_module = importlib.import_module("langgraph.checkpoint.sqlite.aio")
            async_sqlite_saver = getattr(sqlite_module, "AsyncSqliteSaver")

            sqlite_path = runtime_config.checkpoint_sqlite_path
            sqlite_dir = os.path.dirname(sqlite_path)
            if sqlite_dir:
                os.makedirs(sqlite_dir, exist_ok=True)

            context = async_sqlite_saver.from_conn_string(sqlite_path)
            saver = await context.__aenter__()
            logger.info("Using LangGraph SQLite checkpointer: %s", sqlite_path)
            return saver, context
        except Exception as exc:
            logger.warning("Failed to initialize SQLite checkpointer, fallback to InMemorySaver: %s", exc)

    logger.info("Using LangGraph InMemorySaver checkpointer")
    return InMemorySaver(), None
