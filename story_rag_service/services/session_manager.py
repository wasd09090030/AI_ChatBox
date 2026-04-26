"""故事会话管理（SQLite 持久化 + LRU 内存缓存）。

设计要点：
1. `story_sessions` 为会话元信息真值源；
2. 使用 OrderedDict 维护 LRU 热缓存（默认上限 50）；
3. `StoryContext.messages` 仅驻留内存，冷启动时可由
     `load_session_messages()` 从 `story_session_messages` 回填。
"""

import json
import logging
import sqlite3
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from models.story import Message, StoryContext
from repositories.story_session_repository import StorySessionRepository
from services.database import Database

# 模块日志器，用于记录会话缓存与持久化流程中的诊断信息。
logger = logging.getLogger(__name__)

# 会话 LRU 缓存上限，超过后淘汰最久未访问项。
_LRU_MAXSIZE = 50


class SessionManager:
    """管理故事会话生命周期，提供持久化与缓存协同。"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化 SQLite 依赖、会话仓储与内存缓存。"""
        self.db_path = db_path or settings.database_path
        Database(self.db_path)
        self._cache: OrderedDict[str, StoryContext] = OrderedDict()
        self._story_session_repo = StorySessionRepository(self.db_path)
        logger.info("SessionManager initialized (db=%s)", self.db_path)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 WAL，降低并发写锁冲突。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _cache_put(self, session_id: str, context: StoryContext) -> None:
        """写入/刷新会话缓存，并按 LRU 规则淘汰最旧项。"""
        if session_id in self._cache:
            self._cache.move_to_end(session_id)
        else:
            self._cache[session_id] = context
            if len(self._cache) > _LRU_MAXSIZE:
                evicted = next(iter(self._cache))
                self._cache.pop(evicted)
                logger.debug("LRU evict session: %s", evicted)

    def _cache_get(self, session_id: str) -> Optional[StoryContext]:
        """读取缓存命中项，并更新其 LRU 热度。"""
        if session_id not in self._cache:
            return None
        self._cache.move_to_end(session_id)
        return self._cache[session_id]

    def _db_get(self, session_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """从 `story_sessions` 读取会话元信息。"""
        with self._connect() as conn:
            if owner_user_id is None:
                row = conn.execute(
                    "SELECT * FROM story_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM story_sessions WHERE session_id = ? AND owner_user_id = ?",
                    (session_id, owner_user_id),
                ).fetchone()
        return dict(row) if row else None

    def _db_insert(self, session_id: str, **kwargs) -> None:
        """插入会话记录（已存在时忽略）。"""
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO story_sessions
                    (session_id, owner_user_id, world_id, character_card_id, persona_id,
                     first_message_sent, created_at, last_active_at, metadata)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    session_id,
                    kwargs.get("owner_user_id"),
                    kwargs.get("world_id"),
                    kwargs.get("character_card_id"),
                    kwargs.get("persona_id"),
                    now,
                    now,
                    json.dumps(kwargs.get("metadata", {}), ensure_ascii=False),
                ),
            )
            conn.commit()

    def _db_touch(self, session_id: str, owner_user_id: Optional[str] = None) -> None:
        """刷新会话 `last_active_at`，用于最近活跃排序。"""
        with self._connect() as conn:
            if owner_user_id is None:
                conn.execute(
                    "UPDATE story_sessions SET last_active_at = ? WHERE session_id = ?",
                    (datetime.now().isoformat(), session_id),
                )
            else:
                conn.execute(
                    "UPDATE story_sessions SET last_active_at = ? WHERE session_id = ? AND owner_user_id = ?",
                    (datetime.now().isoformat(), session_id, owner_user_id),
                )
            conn.commit()

    # ------------------------------------------------------------------
    # 对外接口（保持向后兼容）
    # ------------------------------------------------------------------

    def get_or_create_session(self, session_id: str, **kwargs) -> StoryContext:
        """获取会话；不存在时创建。

        缓存未命中时先尝试从数据库恢复会话元信息；消息列表仍需按需回填。
        """
        ctx = self._cache_get(session_id)
        if ctx is not None:
            return ctx

        owner_user_id = kwargs.get("owner_user_id")
        row = self._db_get(session_id, owner_user_id=owner_user_id)
        if row:
            ctx = StoryContext(session_id=session_id, messages=[])
            self._cache_put(session_id, ctx)
            self._db_touch(session_id, owner_user_id=owner_user_id)
            logger.info("Restored session from DB: %s", session_id)
            return ctx

        ctx = StoryContext(session_id=session_id, messages=[])
        self._db_insert(session_id, **kwargs)
        self._cache_put(session_id, ctx)
        logger.info("Created new session: %s", session_id)
        return ctx

    def update_session(self, session_id: str, context: StoryContext, owner_user_id: Optional[str] = None) -> None:
        """更新内存上下文并刷新数据库活跃时间。"""
        self._cache_put(session_id, context)
        self._db_touch(session_id, owner_user_id=owner_user_id)
        logger.debug("Updated session: %s messages=%d", session_id, len(context.messages))

    def delete_session(self, session_id: str, owner_user_id: Optional[str] = None) -> bool:
        """从缓存与数据库删除会话；若会话存在则返回 True。"""
        found = session_id in self._cache or self._db_get(session_id, owner_user_id=owner_user_id) is not None
        self._cache.pop(session_id, None)
        with self._connect() as conn:
            if owner_user_id is None:
                conn.execute("DELETE FROM story_sessions WHERE session_id = ?", (session_id,))
            else:
                conn.execute(
                    "DELETE FROM story_sessions WHERE session_id = ? AND owner_user_id = ?",
                    (session_id, owner_user_id),
                )
            conn.commit()
        if found:
            logger.info("Deleted session: %s", session_id)
        return found

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        owner_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按最近活跃时间倒序列出会话。"""
        with self._connect() as conn:
            if owner_user_id is None:
                rows = conn.execute(
                    """
                    SELECT session_id, owner_user_id, world_id, character_card_id, persona_id,
                           first_message_sent, created_at, last_active_at, metadata
                    FROM story_sessions
                    ORDER BY last_active_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT session_id, owner_user_id, world_id, character_card_id, persona_id,
                           first_message_sent, created_at, last_active_at, metadata
                    FROM story_sessions
                    WHERE owner_user_id = ?
                    ORDER BY last_active_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (owner_user_id, limit, offset),
                ).fetchall()
        return [dict(r) for r in rows]

    def load_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        owner_user_id: Optional[str] = None,
    ) -> List[Message]:
        """加载最近未归档消息并转换为 Message 对象。"""
        with self._connect() as conn:
            if owner_user_id is None:
                rows = conn.execute(
                    """
                    SELECT role, content, timestamp
                    FROM story_session_messages
                    WHERE session_id = ? AND archived = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.role, m.content, m.timestamp
                    FROM story_session_messages m
                    JOIN story_sessions s ON s.session_id = m.session_id
                    WHERE m.session_id = ? AND m.archived = 0 AND s.owner_user_id = ?
                    ORDER BY m.timestamp ASC
                    LIMIT ?
                    """,
                    (session_id, owner_user_id, limit),
                ).fetchall()
        messages: List[Message] = []
        for r in rows:
            try:
                ts = datetime.fromisoformat(r["timestamp"]) if r["timestamp"] else datetime.now()
            except Exception:
                ts = datetime.now()
            messages.append(Message(role=r["role"], content=r["content"], timestamp=ts))
        return messages

    def get_session_metadata(self, session_id: str, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """按 session_id 读取持久化会话元数据。"""
        return self._story_session_repo.get_session(session_id, owner_user_id=owner_user_id)

    def mark_first_message_sent(self, session_id: str, owner_user_id: Optional[str] = None) -> bool:
        """将会话首条消息发送标记置为已发送。"""
        return self._story_session_repo.mark_first_message_sent(session_id, owner_user_id=owner_user_id)

    def set_first_message_sent(self, session_id: str, sent: bool, owner_user_id: Optional[str] = None) -> bool:
        """将首条消息发送标记设置为指定布尔值。"""
        return self._story_session_repo.set_first_message_sent(session_id, sent, owner_user_id=owner_user_id)

    def delete_last_message(self, session_id: str, owner_user_id: Optional[str] = None) -> Optional[str]:
        """删除会话最后一条消息（不限角色）。"""
        return self._story_session_repo.delete_last_message(session_id, owner_user_id=owner_user_id)

    def delete_last_assistant_message(self, session_id: str, owner_user_id: Optional[str] = None) -> Optional[str]:
        """删除会话最后一条 assistant 消息。"""
        return self._story_session_repo.delete_last_assistant_message(session_id, owner_user_id=owner_user_id)

    def get_last_user_message(self, session_id: str, owner_user_id: Optional[str] = None) -> Optional[str]:
        """读取会话历史中最后一条 user 消息内容。"""
        return self._story_session_repo.get_last_user_message(session_id, owner_user_id=owner_user_id)

    def remove_last_assistant_from_cache(self, session_id: str) -> None:
        """在数据库侧回滚后，同步修正内存缓存中的最后 assistant 消息。"""
        ctx_obj = self._cache_get(session_id)
        if not ctx_obj:
            return
        if ctx_obj.messages and ctx_obj.messages[-1].role == "assistant":
            ctx_obj.messages.pop()

    def replace_session_messages(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        owner_user_id: Optional[str] = None,
    ) -> int:
        """替换会话全部持久化消息。"""
        return self._story_session_repo.replace_session_messages(
            session_id,
            messages,
            owner_user_id=owner_user_id,
        )

    def rebuild_cached_context(self, session_id: str, messages: List[Message]) -> None:
        """外部重建后，用新消息列表替换缓存上下文。"""
        existing_context = self._cache_get(session_id)
        if existing_context is None:
            existing_context = StoryContext(session_id=session_id, messages=[])
        existing_context.messages = list(messages)
        self._cache_put(session_id, existing_context)
        self._db_touch(session_id)

    def get_session_count(self) -> int:
        """返回数据库中的会话总数。"""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM story_sessions").fetchone()
        return int(row["cnt"]) if row else 0

    def clear_all_sessions(self) -> None:
        """清空缓存与数据库中的全部会话。"""
        self._cache.clear()
        with self._connect() as conn:
            conn.execute("DELETE FROM story_sessions")
            conn.commit()
        logger.info("Cleared all sessions from DB")
