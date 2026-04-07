"""
角色扮演资料映射器：将 SQLite 行记录转换为 Pydantic 模型。
"""

from __future__ import annotations

from datetime import datetime
import sqlite3

from models.roleplay import PersonaProfile, StoryState
from services.roleplay_profiles.db import RoleplaySQLiteStore


def row_to_persona(row: sqlite3.Row) -> PersonaProfile:
    return PersonaProfile(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        title=row["title"],
        traits=RoleplaySQLiteStore.parse_json(row["traits"], []),
        metadata=RoleplaySQLiteStore.parse_json(row["metadata"], {}),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def row_to_story_state(row: sqlite3.Row) -> StoryState:
    return StoryState(
        session_id=row["session_id"],
        chapter=row["chapter"],
        objective=row["objective"],
        conflict=row["conflict"],
        clues=RoleplaySQLiteStore.parse_json(row["clues"], []),
        relationship_arcs=RoleplaySQLiteStore.parse_json(row["relationship_arcs"], {}),
        metadata=RoleplaySQLiteStore.parse_json(row["metadata"], {}),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
