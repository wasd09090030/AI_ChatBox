"""剧本运行时状态仓储（SQLite 实现）。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from models.story_runtime import ScriptRuntimeState


class SqliteStoryRuntimeRepository:
    """持久化 ScriptRuntimeState 的 SQLite 仓储。"""
    def __init__(self, db_path: str):
        """初始化数据库路径并确保运行时状态表可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 Row 访问模式。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        """初始化运行时状态表与查询索引。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS story_runtime_states (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL UNIQUE,
                    owner_user_id TEXT DEFAULT NULL,
                    session_id TEXT NOT NULL,
                    world_id TEXT DEFAULT NULL,
                    script_design_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            existing_columns = {
                row["name"]
                for row in cursor.execute("PRAGMA table_info(story_runtime_states)").fetchall()
            }
            if "owner_user_id" not in existing_columns:
                cursor.execute("ALTER TABLE story_runtime_states ADD COLUMN owner_user_id TEXT DEFAULT NULL")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_story_runtime_owner_user_id "
                "ON story_runtime_states(owner_user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_story_runtime_session_id "
                "ON story_runtime_states(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_story_runtime_script_design_id "
                "ON story_runtime_states(script_design_id)"
            )
            conn.commit()

    def save(self, runtime_state: ScriptRuntimeState, owner_user_id: Optional[str] = None) -> ScriptRuntimeState:
        """按 story_id 写入或更新运行时状态。"""
        payload = json.dumps(runtime_state.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO story_runtime_states (
                    id,
                    story_id,
                    owner_user_id,
                    session_id,
                    world_id,
                    script_design_id,
                    updated_at,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    id = excluded.id,
                    owner_user_id = COALESCE(excluded.owner_user_id, story_runtime_states.owner_user_id),
                    session_id = excluded.session_id,
                    world_id = excluded.world_id,
                    script_design_id = excluded.script_design_id,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    runtime_state.id,
                    runtime_state.story_id,
                    owner_user_id,
                    runtime_state.session_id,
                    runtime_state.world_id,
                    runtime_state.script_design_id,
                    runtime_state.updated_at.isoformat(),
                    payload,
                ),
            )
            conn.commit()
        return runtime_state

    def get_by_story_id(self, story_id: str, owner_user_id: Optional[str] = None) -> Optional[ScriptRuntimeState]:
        """按故事 ID 查询运行时状态。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute(
                    "SELECT payload FROM story_runtime_states WHERE story_id = ?",
                    (story_id,),
                )
            else:
                cursor.execute(
                    "SELECT payload FROM story_runtime_states WHERE story_id = ? AND owner_user_id = ?",
                    (story_id, owner_user_id),
                )
            row = cursor.fetchone()
        if not row:
            return None
        return ScriptRuntimeState(**json.loads(row["payload"]))

    def get_by_id(self, runtime_state_id: str, owner_user_id: Optional[str] = None) -> Optional[ScriptRuntimeState]:
        """按运行时状态 ID 查询记录。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute(
                    "SELECT payload FROM story_runtime_states WHERE id = ?",
                    (runtime_state_id,),
                )
            else:
                cursor.execute(
                    "SELECT payload FROM story_runtime_states WHERE id = ? AND owner_user_id = ?",
                    (runtime_state_id, owner_user_id),
                )
            row = cursor.fetchone()
        if not row:
            return None
        return ScriptRuntimeState(**json.loads(row["payload"]))

    def delete_by_story_id(self, story_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按故事 ID 删除运行时状态并返回是否成功。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute(
                    "DELETE FROM story_runtime_states WHERE story_id = ?",
                    (story_id,),
                )
            else:
                cursor.execute(
                    "DELETE FROM story_runtime_states WHERE story_id = ? AND owner_user_id = ?",
                    (story_id, owner_user_id),
                )
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted
