"""故事/会话一致性重建服务。

当故事正文调整后，该服务负责重建持久化会话状态，确保后续生成基于最新文本继续。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from application.memory import build_memory_update_event, persist_memory_update_events
from models.story import Message


def _parse_iso_timestamp(value: Optional[str], fallback: datetime) -> datetime:
    """解析 ISO 时间字符串，解析失败时回退到 fallback。"""
    if not value:
        return fallback
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return fallback


class StoryConsistencyRebuildService:
    """基于故事片段重建会话消息、摘要状态与历史索引。"""

    def __init__(
        self,
        session_manager,
        summary_memory_manager,
        history_manager,
        story_runtime_manager=None,
        entity_state_manager=None,
    ):
        """初始化一致性重建服务。"""
        self.session_manager = session_manager
        self.summary_memory_manager = summary_memory_manager
        self.history_manager = history_manager
        self.story_runtime_manager = story_runtime_manager
        self.entity_state_manager = entity_state_manager

    def rebuild_story_state(
        self,
        *,
        story,
        session_id: str,
        source: str = "story_adjustment_commit",
    ) -> dict[str, Any]:
        """在故事正文调整后重建会话一致性状态。

        重建内容包括：
        1. 会话消息与缓存上下文；
        2. 摘要记忆清理；
        3. 历史索引重建；
        4. 可选实体状态重建。
        """
        self.session_manager.get_or_create_session(session_id, world_id=story.world_id)
        memory_updates: list[dict[str, Any]] = []

        now = datetime.now()
        persisted_messages: list[dict[str, Any]] = []
        cached_messages: list[Message] = []
        message_index = 0

        for segment in story.segments:
            # 通过微秒偏移保证同段 user/assistant 消息时间顺序稳定。
            base_time = _parse_iso_timestamp(getattr(segment, "timestamp", None), now)
            user_time = base_time + timedelta(microseconds=message_index)
            assistant_time = base_time + timedelta(microseconds=message_index + 1)
            message_index += 2

            prompt_text = (segment.prompt or "").strip()
            if prompt_text:
                persisted_messages.append(
                    {
                        "role": "user",
                        "content": prompt_text,
                        "timestamp": user_time.isoformat(),
                    }
                )
                cached_messages.append(Message(role="user", content=prompt_text, timestamp=user_time))

            content_text = (segment.content or "").strip()
            if content_text:
                persisted_messages.append(
                    {
                        "role": "assistant",
                        "content": content_text,
                        "timestamp": assistant_time.isoformat(),
                    }
                )
                cached_messages.append(Message(role="assistant", content=content_text, timestamp=assistant_time))

        self.session_manager.replace_session_messages(session_id, persisted_messages)
        self.session_manager.set_first_message_sent(session_id, bool(persisted_messages))
        self.session_manager.rebuild_cached_context(session_id, cached_messages)
        memory_updates.append(
            build_memory_update_event(
                session_id=session_id,
                memory_layer="episodic",
                action="rebuilt",
                source=source,
                title="会话消息已按故事正文重建",
                after={
                    "message_count": len(persisted_messages),
                    "segment_count": len(getattr(story, "segments", []) or []),
                },
            )
        )

        summary_reset = self.summary_memory_manager.delete_summary(session_id)
        if summary_reset:
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="semantic",
                    action="reset",
                    source=source,
                    memory_key="conversation_summary",
                    title="摘要记忆已重置",
                    reason="故事正文已提交修改，需要等待新上下文重建摘要",
                )
            )

        warnings: list[str] = []
        history_reindexed = False
        entity_state_rebuilt = False
        try:
            # 历史向量索引重建失败不阻断主流程，作为 warning 透出。
            self.history_manager.rebuild_session_history(session_id, story.world_id, cached_messages)
            history_reindexed = True
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="episodic",
                    action="reindexed",
                    source=source,
                    memory_key="conversation_history_index",
                    title="历史向量索引已重建",
                    after={"indexed_message_count": len(cached_messages)},
                )
            )
        except Exception as exc:
            warnings.append(f"历史索引重建失败: {exc}")
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="episodic",
                    action="reindexed",
                    source=source,
                    memory_key="conversation_history_index",
                    title="历史向量索引重建失败",
                    reason=str(exc),
                    status="failed",
                )
            )

        updates_to_persist = list(memory_updates)

        if self.entity_state_manager is not None:
            runtime_state = None
            if self.story_runtime_manager is not None:
                runtime_state = self.story_runtime_manager.get_runtime_state(story.id)
            try:
                entity_rebuild = self.entity_state_manager.rebuild_story_state(
                    story=story,
                    session_id=session_id,
                    runtime_state=runtime_state,
                    persist=True,
                    source=source,
                )
                entity_state_rebuilt = bool(entity_rebuild.rebuilt)
                memory_updates.extend(entity_rebuild.memory_updates)
                warnings.extend(entity_rebuild.warnings)
            except Exception as exc:
                warnings.append(f"实体状态重建失败: {exc}")
                memory_updates.append(
                    build_memory_update_event(
                        session_id=session_id,
                        memory_layer="entity_state",
                        action="rebuilt",
                        source=source,
                        title="实体状态重建失败",
                        reason=str(exc),
                        status="failed",
                    )
                )
                updates_to_persist = list(memory_updates)

        persist_memory_update_events(updates_to_persist)
        return {
            "summary_reset": summary_reset,
            "history_reindexed": history_reindexed,
            "entity_state_rebuilt": entity_state_rebuilt,
            "warnings": warnings,
            "memory_updates": memory_updates,
        }
