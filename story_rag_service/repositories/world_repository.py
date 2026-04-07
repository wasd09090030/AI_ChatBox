"""
World repository abstractions and implementations.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.world import World


class WorldRepository:
    def save(self, world: World) -> World:
        raise NotImplementedError

    def get(self, world_id: str) -> Optional[World]:
        raise NotImplementedError

    def list_all(self) -> List[World]:
        raise NotImplementedError

    def delete(self, world_id: str) -> bool:
        raise NotImplementedError

    def exists(self, world_id: str) -> bool:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class JsonWorldRepository(WorldRepository):
    def __init__(self, storage_path: str = "./data/worlds.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[World]:
        if not self.storage_path.exists():
            return []
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [World(**item) for item in data]

    def _save_all(self, worlds: List[World]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump([world.model_dump(mode="json") for world in worlds], file, ensure_ascii=False, indent=2)

    def save(self, world: World) -> World:
        worlds = {item.id: item for item in self._load_all()}
        worlds[world.id] = world
        self._save_all(list(worlds.values()))
        return world

    def get(self, world_id: str) -> Optional[World]:
        worlds = {item.id: item for item in self._load_all()}
        return worlds.get(world_id)

    def list_all(self) -> List[World]:
        return self._load_all()

    def delete(self, world_id: str) -> bool:
        worlds = self._load_all()
        original_count = len(worlds)
        worlds = [item for item in worlds if item.id != world_id]
        if len(worlds) == original_count:
            return False
        self._save_all(worlds)
        return True

    def exists(self, world_id: str) -> bool:
        return self.get(world_id) is not None

    def count(self) -> int:
        return len(self._load_all())


class SqliteWorldRepository(WorldRepository):
    def __init__(self, db_path: str = "./data/chatbox.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS worlds (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, world: World) -> World:
        payload = json.dumps(world.model_dump(mode="json"), ensure_ascii=False)
        updated_at = str(world.updated_at)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO worlds (id, name, updated_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (world.id, world.name, updated_at, payload),
            )
            conn.commit()
        return world

    def get(self, world_id: str) -> Optional[World]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM worlds WHERE id = ?", (world_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return World(**json.loads(row[0]))

    def list_all(self) -> List[World]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM worlds ORDER BY updated_at DESC")
            rows = cursor.fetchall()
        return [World(**json.loads(row[0])) for row in rows]

    def delete(self, world_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def exists(self, world_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM worlds WHERE id = ? LIMIT 1", (world_id,))
            return cursor.fetchone() is not None

    def count(self) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(1) FROM worlds")
            row = cursor.fetchone()
        return int(row[0]) if row else 0
