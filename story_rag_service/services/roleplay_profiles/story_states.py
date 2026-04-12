"""
故事状态仓储：处理 story_states 表的读取与 upsert。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from models.roleplay import StoryState, StoryStateUpdate
from services.roleplay_profiles.db import RoleplaySQLiteStore
from services.roleplay_profiles.mappers import row_to_story_state


class StoryStateStore:
    """作用：定义 StoryStateStore 类型，承载本模块核心状态与行为。"""
    def __init__(self, db: RoleplaySQLiteStore):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self._db = db

    def get(self, session_id: str) -> Optional[StoryState]:
        """功能：获取目标对象。"""
        with self._db.connect() as conn:
            row = conn.execute("SELECT * FROM story_states WHERE session_id = ?", (session_id,)).fetchone()
        return row_to_story_state(row) if row else None

    def upsert(self, session_id: str, data: StoryStateUpdate) -> StoryState:
        """功能：新增或更新目标对象。"""
        existing = self.get(session_id)
        payload = data.model_dump(exclude_unset=True)

        if existing is None:
            state = StoryState(
                session_id=session_id,
                chapter=payload.get("chapter"),
                objective=payload.get("objective"),
                conflict=payload.get("conflict"),
                clues=payload.get("clues", []),
                relationship_arcs=payload.get("relationship_arcs", {}),
                metadata=payload.get("metadata", {}),
                updated_at=datetime.now(),
            )
            with self._db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO story_states (
                        session_id, chapter, objective, conflict,
                        clues, relationship_arcs, metadata, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state.session_id,
                        state.chapter,
                        state.objective,
                        state.conflict,
                        json.dumps(state.clues, ensure_ascii=False),
                        json.dumps(state.relationship_arcs, ensure_ascii=False),
                        json.dumps(state.metadata, ensure_ascii=False),
                        state.updated_at.isoformat(),
                    ),
                )
                conn.commit()
            return state

        merged = existing.model_copy(update=payload)
        merged.updated_at = datetime.now()

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE story_states
                SET chapter = ?, objective = ?, conflict = ?, clues = ?,
                    relationship_arcs = ?, metadata = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (
                    merged.chapter,
                    merged.objective,
                    merged.conflict,
                    json.dumps(merged.clues, ensure_ascii=False),
                    json.dumps(merged.relationship_arcs, ensure_ascii=False),
                    json.dumps(merged.metadata, ensure_ascii=False),
                    merged.updated_at.isoformat(),
                    session_id,
                ),
            )
            conn.commit()

        return merged
