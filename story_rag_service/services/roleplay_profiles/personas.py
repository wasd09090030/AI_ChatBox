"""
Persona 仓储：仅处理 persona_profiles 表的 CRUD。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import List, Optional

from models.roleplay import PersonaProfile, PersonaProfileCreate, PersonaProfileUpdate
from services.roleplay_profiles.db import RoleplaySQLiteStore
from services.roleplay_profiles.mappers import row_to_persona


class PersonaStore:
    """作用：定义 PersonaStore 类型，承载本模块核心状态与行为。"""
    def __init__(self, db: RoleplaySQLiteStore):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self._db = db

    def list(self) -> List[PersonaProfile]:
        """功能：查询并返回目标对象列表。"""
        with self._db.connect() as conn:
            rows = conn.execute("SELECT * FROM persona_profiles ORDER BY updated_at DESC").fetchall()
        return [row_to_persona(row) for row in rows]

    def get(self, persona_id: str) -> Optional[PersonaProfile]:
        """功能：获取目标对象。"""
        with self._db.connect() as conn:
            row = conn.execute("SELECT * FROM persona_profiles WHERE id = ?", (persona_id,)).fetchone()
        return row_to_persona(row) if row else None

    def create(self, data: PersonaProfileCreate) -> PersonaProfile:
        """功能：创建目标对象。"""
        now = datetime.now().isoformat()
        persona_id = str(uuid.uuid4())
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO persona_profiles (
                    id, name, description, title, traits, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    persona_id,
                    data.name,
                    data.description,
                    data.title,
                    json.dumps(data.traits, ensure_ascii=False),
                    json.dumps(data.metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            conn.commit()
        created = self.get(persona_id)
        if created is None:
            raise RuntimeError("Failed to create persona")
        return created

    def update(self, persona_id: str, data: PersonaProfileUpdate) -> Optional[PersonaProfile]:
        """功能：更新目标对象。"""
        existing = self.get(persona_id)
        if existing is None:
            return None

        updates = []
        params = []
        payload = data.model_dump(exclude_unset=True)

        for key in ["name", "description", "title"]:
            if key in payload:
                updates.append(f"{key} = ?")
                params.append(payload[key])

        if "traits" in payload:
            updates.append("traits = ?")
            params.append(json.dumps(payload["traits"], ensure_ascii=False))
        if "metadata" in payload:
            updates.append("metadata = ?")
            params.append(json.dumps(payload["metadata"], ensure_ascii=False))

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(persona_id)

        with self._db.connect() as conn:
            conn.execute(f"UPDATE persona_profiles SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        return self.get(persona_id)

    def delete(self, persona_id: str) -> bool:
        """功能：删除目标对象。"""
        with self._db.connect() as conn:
            cursor = conn.execute("DELETE FROM persona_profiles WHERE id = ?", (persona_id,))
            conn.commit()
            return cursor.rowcount > 0
