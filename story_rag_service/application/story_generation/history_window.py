"""短期记忆窗口格式化与归档逻辑。

核心目标：维持“最近消息用于即时生成、更早消息进入长期检索”的双层记忆结构。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


def format_recent_history_messages(
    *,
    context: Any,
    recent_message_count: int,
    format_history_fn: Callable[[List[Any]], List[Any]],
) -> List[Any]:
    """格式化短期窗口内历史消息，用于本轮 LLM 输入。"""
    recent_window_size = recent_message_count * 2
    # 过滤掉最后一条（通常是当前轮刚追加的 user 输入），避免重复注入。
    recent_messages = context.messages[max(0, len(context.messages) - recent_window_size - 1) : -1]
    return format_history_fn(recent_messages)


def archive_messages_outside_window(
    *,
    history_manager: Optional[Any],
    context: Any,
    session_id: str,
    world_id: Optional[str],
    recent_message_count: int,
    log_prefix: str = "",
) -> int:
    """将超出短期记忆窗口的消息归档到长期记忆。

    返回值为成功归档的消息数量。
    """
    if not history_manager:
        logger.warning("%shistory_manager is None, cannot archive messages", log_prefix)
        return 0

    # 保留最近 N 轮（user+assistant）在短期窗口中。
    messages_to_keep = recent_message_count * 2
    current_total = len(context.messages)
    logger.info(
        "%sArchive check: current_total=%s, messages_to_keep=%s",
        log_prefix,
        current_total,
        messages_to_keep,
    )

    if current_total <= messages_to_keep:
        logger.info(
            "%sNo archiving needed: current_total (%s) <= messages_to_keep (%s)",
            log_prefix,
            current_total,
            messages_to_keep,
        )
        return 0

    messages_beyond_window = current_total - messages_to_keep
    # 从窗口边界附近回看一轮，降低半轮上下文被截断的概率。
    start_idx = messages_beyond_window - 2 if messages_beyond_window >= 2 else 0
    end_idx = messages_beyond_window
    logger.info(
        "%sArchiving range: start_idx=%s, end_idx=%s, messages_beyond_window=%s",
        log_prefix,
        start_idx,
        end_idx,
        messages_beyond_window,
    )

    archived_count = 0
    for idx in range(start_idx, end_idx):
        message = context.messages[idx]
        try:
            history_manager.add_message_to_rag(
                session_id=session_id,
                world_id=world_id,
                role=message.role,
                content=message.content,
                turn_number=idx // 2 + 1,
            )
            logger.info(
                "%s✓ Archived %s message from turn %s to long-term memory",
                log_prefix,
                message.role,
                idx // 2 + 1,
            )
            archived_count += 1
        except Exception as exc:
            logger.error("%sFailed to archive message %s: %s", log_prefix, idx, exc, exc_info=True)
    return archived_count
