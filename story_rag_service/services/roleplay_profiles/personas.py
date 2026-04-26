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
    """人格卡仓储服务（persona_profiles 表）。"""
    def __init__(self, db: RoleplaySQLiteStore):
        """注入底层 SQLite 存储对象。"""
        self._db = db

    def list(self, owner_user_id: Optional[str] = None) -> List[PersonaProfile]:
        """查询全部人格卡，按更新时间倒序返回。"""
        with self._db.connect() as conn:
            if owner_user_id is None:
                rows = conn.execute(
                    "SELECT * FROM persona_profiles ORDER BY updated_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM persona_profiles WHERE owner_user_id = ? ORDER BY updated_at DESC",
                    (owner_user_id,),
                ).fetchall()
        return [row_to_persona(row) for row in rows]

    def get(self, persona_id: str, owner_user_id: Optional[str] = None) -> Optional[PersonaProfile]:
        """按 ID 查询单个人格卡。"""
        with self._db.connect() as conn:
            if owner_user_id is None:
                row = conn.execute(
                    "SELECT * FROM persona_profiles WHERE id = ?",
                    (persona_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM persona_profiles WHERE id = ? AND owner_user_id = ?",
                    (persona_id, owner_user_id),
                ).fetchone()
        return row_to_persona(row) if row else None

    def create(self, data: PersonaProfileCreate, owner_user_id: Optional[str] = None) -> PersonaProfile:
        """创建人格卡并返回持久化后的对象。"""
        now = datetime.now().isoformat()
        persona_id = str(uuid.uuid4())
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO persona_profiles (
                    id, owner_user_id, name, description, title, traits, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    persona_id,
                    owner_user_id,
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
        created = self.get(persona_id, owner_user_id=owner_user_id)
        if created is None:
            raise RuntimeError("Failed to create persona")
        return created

    def update(
        self,
        persona_id: str,
        data: PersonaProfileUpdate,
        owner_user_id: Optional[str] = None,
    ) -> Optional[PersonaProfile]:
        """按补丁字段更新人格卡；不存在时返回 None。"""
        existing = self.get(persona_id, owner_user_id=owner_user_id)
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
        query = f"UPDATE persona_profiles SET {', '.join(updates)} WHERE id = ?"
        if owner_user_id is not None:
            query += " AND owner_user_id = ?"
            params.append(owner_user_id)

        with self._db.connect() as conn:
            conn.execute(query, params)
            conn.commit()

        return self.get(persona_id, owner_user_id=owner_user_id)

    def delete(self, persona_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除人格卡并返回是否成功。"""
        with self._db.connect() as conn:
            if owner_user_id is None:
                cursor = conn.execute(
                    "DELETE FROM persona_profiles WHERE id = ?",
                    (persona_id,),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM persona_profiles WHERE id = ? AND owner_user_id = ?",
                    (persona_id, owner_user_id),
                )
            conn.commit()
            return cursor.rowcount > 0
