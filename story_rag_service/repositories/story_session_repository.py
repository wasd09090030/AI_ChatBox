"""
故事会话仓储抽象与 SQLite 实现。

该模块将直接 SQL 操作与 API 路由、管理器逻辑隔离。
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Dict, Optional


class StorySessionRepository:
    """为 story_sessions 与 story_session_messages 提供读写辅助。"""

    def __init__(self, db_path: str):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """功能：处理 connect。"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """按 session_id 返回会话元数据行。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM story_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def mark_first_message_sent(self, session_id: str) -> bool:
        """将会话 first_message_sent 置为 1；行存在时返回 True。"""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE story_sessions SET first_message_sent = 1 WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def set_first_message_sent(self, session_id: str, sent: bool) -> bool:
        """将 first_message_sent 设置为指定布尔值。"""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE story_sessions SET first_message_sent = ? WHERE session_id = ?",
                (1 if sent else 0, session_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def replace_session_messages(self, session_id: str, messages: list[Dict[str, Any]]) -> int:
        """替换会话已持久化的全部消息。"""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM story_session_messages WHERE session_id = ?",
                (session_id,),
            )
            for item in messages:
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                role = str(item.get("role") or "").strip() or "assistant"
                timestamp = item.get("timestamp")
                conn.execute(
                    """
                    INSERT INTO story_session_messages
                        (id, session_id, role, content, timestamp, token_estimate, archived)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        str(uuid.uuid4()),
                        session_id,
                        role,
                        content,
                        timestamp,
                        max(1, len(content) // 4),
                    ),
                )
            conn.commit()
            count_row = conn.execute(
                "SELECT COUNT(1) AS cnt FROM story_session_messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(count_row["cnt"]) if count_row else 0

    def delete_last_message(self, session_id: str) -> Optional[str]:
        """
        删除会话中最新的未归档消息。

        返回被删除的消息 ID；若不存在消息则返回 None。
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM story_session_messages
                WHERE session_id = ? AND archived = 0
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None

            message_id = str(row["id"])
            conn.execute(
                "DELETE FROM story_session_messages WHERE id = ?",
                (message_id,),
            )
            conn.commit()
            return message_id

    def delete_last_assistant_message(self, session_id: str) -> Optional[str]:
        """
        删除会话中最新的 assistant 消息。

        返回被删除的消息 ID；若不存在 assistant 消息则返回 None。
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM story_session_messages
                WHERE session_id = ? AND role = 'assistant' AND archived = 0
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None

            message_id = str(row["id"])
            conn.execute(
                "DELETE FROM story_session_messages WHERE id = ?",
                (message_id,),
            )
            conn.commit()
            return message_id

    def get_last_user_message(self, session_id: str) -> Optional[str]:
        """返回最新用户消息内容；未找到时返回 None。"""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT content
                FROM story_session_messages
                WHERE session_id = ? AND role = 'user' AND archived = 0
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return str(row["content"])
