"""实体状态快照仓储（SQLite 实现）。

维护每个故事当前时刻的实体状态投影结果，支持按故事/会话查询与覆盖写入。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.entity_state import EntityStateSnapshot


class SqliteEntityStateRepository:
    """基于 SQLite 的实体状态快照仓储。"""
    def __init__(self, db_path: str):
        """初始化数据库路径并确保快照表结构可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 Row 访问模式。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        """初始化快照表与常用查询索引。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS story_entity_states (
                    story_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (story_id, entity_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_story_entity_states_session_id
                ON story_entity_states(session_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_story_entity_states_entity_type
                ON story_entity_states(entity_type)
                """
            )
            conn.commit()

    def replace_story_states(
        self,
        *,
        story_id: str,
        session_id: str,
        states: List[EntityStateSnapshot],
    ) -> List[EntityStateSnapshot]:
        """用新快照全量替换指定故事的实体状态。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM story_entity_states WHERE story_id = ?",
                (story_id,),
            )
            cursor.executemany(
                """
                INSERT INTO story_entity_states (
                    story_id,
                    session_id,
                    entity_id,
                    entity_type,
                    updated_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        story_id,
                        session_id,
                        state.entity_id,
                        state.entity_type,
                        state.updated_at.isoformat(),
                        json.dumps(state.model_dump(mode="json"), ensure_ascii=False),
                    )
                    for state in states
                ],
            )
            conn.commit()
        return states

    def list_by_story_id(
        self,
        story_id: str,
        *,
        entity_type: Optional[str] = None,
    ) -> List[EntityStateSnapshot]:
        """按故事 ID 查询实体状态快照，可按实体类型过滤。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute(
                    """
                    SELECT payload
                    FROM story_entity_states
                    WHERE story_id = ? AND entity_type = ?
                    ORDER BY updated_at DESC, entity_id ASC
                    """,
                    (story_id, entity_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT payload
                    FROM story_entity_states
                    WHERE story_id = ?
                    ORDER BY updated_at DESC, entity_id ASC
                    """,
                    (story_id,),
                )
            rows = cursor.fetchall()
        return [EntityStateSnapshot(**json.loads(row["payload"])) for row in rows]

    def list_by_session_id(
        self,
        session_id: str,
        *,
        entity_type: Optional[str] = None,
    ) -> List[EntityStateSnapshot]:
        """按会话 ID 查询实体状态快照，可按实体类型过滤。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute(
                    """
                    SELECT payload
                    FROM story_entity_states
                    WHERE session_id = ? AND entity_type = ?
                    ORDER BY updated_at DESC, entity_id ASC
                    """,
                    (session_id, entity_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT payload
                    FROM story_entity_states
                    WHERE session_id = ?
                    ORDER BY updated_at DESC, entity_id ASC
                    """,
                    (session_id,),
                )
            rows = cursor.fetchall()
        return [EntityStateSnapshot(**json.loads(row["payload"])) for row in rows]

    def delete_by_story_id(self, story_id: str) -> int:
        """删除指定故事下的所有实体状态快照并返回数量。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM story_entity_states WHERE story_id = ?",
                (story_id,),
            )
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)
