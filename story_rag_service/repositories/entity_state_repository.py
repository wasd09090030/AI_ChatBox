"""
SQLite repository for current entity state snapshots.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.entity_state import EntityStateSnapshot


class SqliteEntityStateRepository:
    """作用：定义 SqliteEntityStateRepository 服务对象，用于封装对应领域流程。"""
    def __init__(self, db_path: str):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        """功能：处理 connect。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        """功能：处理 init table。"""
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
        """功能：处理 replace 故事 states。"""
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
        """功能：查询并返回 by 故事ID列表。"""
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
        """功能：查询并返回 by 会话 ID列表。"""
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
        """功能：删除 by 故事ID。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM story_entity_states WHERE story_id = ?",
                (story_id,),
            )
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)
