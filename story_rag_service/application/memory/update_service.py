"""文件说明：后端应用层用例编排。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from application.story_generation_common import archive_messages_outside_window
from application.memory.events import build_memory_update_event, summarize_summary_snapshot
from application.memory.journal import persist_memory_update_events
from config import settings
from services.story_generation.context_helpers import persist_message_to_db
from services.story_generation.summary_helpers import (
    async_maybe_update_summary_memory,
    maybe_update_summary_memory,
)

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class MemoryUpdateService:
    """封装会话消息、情节记忆索引与摘要记忆的更新流程。"""
    def __init__(
        self,
        *,
        history_manager=None,
        summary_memory_manager=None,
        recent_message_count: int = 5,
    ):
        """注入记忆相关依赖并配置历史窗口参数。"""
        self.history_manager = history_manager
        self.summary_memory_manager = summary_memory_manager
        self.recent_message_count = recent_message_count

    def persist_message(self, session_id: str, role: str, content: str) -> None:
        """将单条消息写入数据库，异常时仅记录告警不打断主流程。"""
        try:
            persist_message_to_db(settings.database_path, session_id, role, content)
        except Exception as exc:
            logger.warning("Failed to persist message to DB: %s", exc)

    def persist_turn(self, *, session_id: str, user_input: str, assistant_output: str) -> None:
        """按一问一答写入当前轮次消息。"""
        self.persist_message(session_id, "user", user_input)
        self.persist_message(session_id, "assistant", assistant_output)

    def update_episodic_index(
        self,
        *,
        session_id: str,
        world_id: Optional[str],
        context,
        log_prefix: str = "",
    ) -> int:
        """归档窗口外会话消息并更新情节记忆向量索引。"""
        return archive_messages_outside_window(
            history_manager=self.history_manager,
            context=context,
            session_id=session_id,
            world_id=world_id,
            recent_message_count=self.recent_message_count,
            log_prefix=log_prefix,
        )

    def maybe_update_summary(
        self,
        *,
        session_id: str,
        world_id: Optional[str],
        context,
        activation_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """根据配置与触发条件同步更新摘要记忆。"""
        return maybe_update_summary_memory(
            summary_memory_manager=self.summary_memory_manager,
            summary_memory_enabled=settings.rp_summary_memory_enabled,
            session_id=session_id,
            world_id=world_id,
            context=context,
            activation_logs=activation_logs,
        )

    async def async_maybe_update_summary(
        self,
        *,
        session_id: str,
        world_id: Optional[str],
        context,
        activation_logs: List[Dict[str, Any]],
        llm: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """根据配置与触发条件异步更新摘要记忆。"""
        return await async_maybe_update_summary_memory(
            summary_memory_manager=self.summary_memory_manager,
            summary_memory_enabled=settings.rp_summary_memory_enabled,
            session_id=session_id,
            world_id=world_id,
            context=context,
            activation_logs=activation_logs,
            llm=llm,
        )

    def get_summary_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        """读取当前会话摘要快照；未启用摘要管理时返回空。"""
        if not self.summary_memory_manager:
            return None
        return self.summary_memory_manager.get_summary(session_id)

    def run_post_generation_updates(
        self,
        *,
        session_id: str,
        world_id: Optional[str],
        context,
        user_input: str,
        assistant_output: str,
        activation_logs: List[Dict[str, Any]],
        summary_update_mode: str = "sync",
        llm: Any = None,
        log_prefix: str = "",
        source: str = "generate",
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
    ) -> Dict[str, Any]:
        """在生成完成后落库消息、更新记忆并记录更新事件。"""
        current_turn = len(getattr(context, "messages", []) or []) // 2
        memory_updates: List[Dict[str, Any]] = []
        before_summary = self.get_summary_snapshot(session_id)

        self.persist_turn(
            session_id=session_id,
            user_input=user_input,
            assistant_output=assistant_output,
        )
        memory_updates.append(
            build_memory_update_event(
                session_id=session_id,
                memory_layer="episodic",
                action="updated",
                source=source,
                source_turn=current_turn,
                memory_key="story_session_messages",
                title="原始会话消息已写入",
                after={
                    "roles": ["user", "assistant"],
                    "user_input_preview": user_input[:80],
                    "assistant_output_preview": assistant_output[:120],
                },
            )
        )

        archived_count = self.update_episodic_index(
            session_id=session_id,
            world_id=world_id,
            context=context,
            log_prefix=log_prefix,
        )
        if archived_count > 0:
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="episodic",
                    action="updated",
                    source=source,
                    source_turn=current_turn,
                    memory_key="conversation_history_index",
                    title="历史向量索引已更新",
                    after={"archived_message_count": archived_count},
                )
            )

        if summary_update_mode == "async":
            persist_memory_update_events(
                memory_updates,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )
            asyncio.create_task(
                self.async_maybe_update_summary(
                    session_id=session_id,
                    world_id=world_id,
                    context=context,
                    activation_logs=activation_logs,
                    llm=llm,
                )
            )
            return {
                "summary_snapshot": self.get_summary_snapshot(session_id),
                "memory_updates": memory_updates,
            }

        summary_snapshot = self.maybe_update_summary(
            session_id=session_id,
            world_id=world_id,
            context=context,
            activation_logs=activation_logs,
        )
        if summary_snapshot != before_summary:
            summary_action = "created" if not before_summary and summary_snapshot else "merged"
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="semantic",
                    action=summary_action,
                    source=source,
                    source_turn=current_turn,
                    memory_key="conversation_summary",
                    title="摘要记忆已更新",
                    before=summarize_summary_snapshot(before_summary),
                    after=summarize_summary_snapshot(summary_snapshot),
                )
            )

        persist_memory_update_events(
            memory_updates,
            operation_id=operation_id,
            sequence_start=sequence_start,
        )
        return {
            "summary_snapshot": summary_snapshot,
            "memory_updates": memory_updates,
        }
