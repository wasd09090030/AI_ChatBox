"""
SQLite repository for script runtime state.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from models.story_runtime import ScriptRuntimeState


class SqliteStoryRuntimeRepository:
    """作用：定义 SqliteStoryRuntimeRepository 服务对象，用于封装对应领域流程。"""
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
                CREATE TABLE IF NOT EXISTS story_runtime_states (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL,
                    world_id TEXT DEFAULT NULL,
                    script_design_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_story_runtime_states_session_id "
                "ON story_runtime_states(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_story_runtime_states_script_design_id "
                "ON story_runtime_states(script_design_id)"
            )
            conn.commit()

    def save(self, runtime_state: ScriptRuntimeState) -> ScriptRuntimeState:
        """功能：保存目标对象。"""
        payload = json.dumps(runtime_state.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO story_runtime_states (
                    id,
                    story_id,
                    session_id,
                    world_id,
                    script_design_id,
                    updated_at,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    id = excluded.id,
                    session_id = excluded.session_id,
                    world_id = excluded.world_id,
                    script_design_id = excluded.script_design_id,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    runtime_state.id,
                    runtime_state.story_id,
                    runtime_state.session_id,
                    runtime_state.world_id,
                    runtime_state.script_design_id,
                    runtime_state.updated_at.isoformat(),
                    payload,
                ),
            )
            conn.commit()
        return runtime_state

    def get_by_story_id(self, story_id: str) -> Optional[ScriptRuntimeState]:
        """功能：获取 by 故事ID。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM story_runtime_states WHERE story_id = ?",
                (story_id,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return ScriptRuntimeState(**json.loads(row["payload"]))

    def get_by_id(self, runtime_state_id: str) -> Optional[ScriptRuntimeState]:
        """功能：获取 by ID。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM story_runtime_states WHERE id = ?",
                (runtime_state_id,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return ScriptRuntimeState(**json.loads(row["payload"]))

    def delete_by_story_id(self, story_id: str) -> bool:
        """功能：删除 by 故事ID。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM story_runtime_states WHERE story_id = ?",
                (story_id,),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted
