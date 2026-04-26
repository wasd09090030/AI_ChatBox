"""世界观仓储接口与实现。

提供 JSON 与 SQLite 两种持久化后端，统一对外暴露世界观 CRUD 能力。
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.world import World


class WorldRepository:
    """世界观仓储抽象接口。"""
    def save(self, world: World, owner_user_id: Optional[str] = None) -> World:
        """新增或更新世界观记录，并返回最新对象。"""
        raise NotImplementedError

    def get(self, world_id: str, owner_user_id: Optional[str] = None) -> Optional[World]:
        """按世界观 ID 查询单个记录。"""
        raise NotImplementedError

    def list_all(self, owner_user_id: Optional[str] = None) -> List[World]:
        """查询全部世界观记录。"""
        raise NotImplementedError

    def delete(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除世界观，返回是否删除成功。"""
        raise NotImplementedError

    def exists(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """判断指定世界观是否存在。"""
        raise NotImplementedError

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """返回世界观总数。"""
        raise NotImplementedError


class JsonWorldRepository(WorldRepository):
    """基于 JSON 文件的世界观仓储实现。"""
    def __init__(self, storage_path: str = "./data/worlds.json"):
        """初始化 JSON 存储路径并确保父目录存在。"""
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[World]:
        """从 JSON 文件加载全部世界观记录。"""
        if not self.storage_path.exists():
            return []
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [World(**item) for item in data]

    def _save_all(self, worlds: List[World]) -> None:
        """将全部世界观记录覆写保存到 JSON 文件。"""
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump([world.model_dump(mode="json") for world in worlds], file, ensure_ascii=False, indent=2)

    def save(self, world: World, owner_user_id: Optional[str] = None) -> World:
        """以 ID 为键保存世界观（存在则更新，不存在则新增）。"""
        worlds = {item.id: item for item in self._load_all()}
        worlds[world.id] = world
        self._save_all(list(worlds.values()))
        return world

    def get(self, world_id: str, owner_user_id: Optional[str] = None) -> Optional[World]:
        """按 ID 从 JSON 记录中查询世界观。"""
        worlds = {item.id: item for item in self._load_all()}
        return worlds.get(world_id)

    def list_all(self, owner_user_id: Optional[str] = None) -> List[World]:
        """返回 JSON 中的全部世界观记录。"""
        return self._load_all()

    def delete(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除 JSON 中的世界观记录。"""
        worlds = self._load_all()
        original_count = len(worlds)
        worlds = [item for item in worlds if item.id != world_id]
        if len(worlds) == original_count:
            return False
        self._save_all(worlds)
        return True

    def exists(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """判断 JSON 存储中是否存在指定世界观。"""
        return self.get(world_id) is not None

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """统计 JSON 存储中的世界观数量。"""
        return len(self._load_all())


class SqliteWorldRepository(WorldRepository):
    """基于 SQLite 的世界观仓储实现。"""
    def __init__(self, db_path: str = "./data/chatbox.db"):
        """初始化数据库路径并确保 worlds 表可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        """创建 SQLite 连接。"""
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        """初始化 worlds 表结构。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS worlds (
                    id TEXT PRIMARY KEY,
                    owner_user_id TEXT DEFAULT NULL,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            existing_columns = {
                row[1]
                for row in cursor.execute("PRAGMA table_info(worlds)").fetchall()
            }
            if "owner_user_id" not in existing_columns:
                cursor.execute("ALTER TABLE worlds ADD COLUMN owner_user_id TEXT DEFAULT NULL")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worlds_owner_user_id ON worlds(owner_user_id)")
            conn.commit()

    def save(self, world: World, owner_user_id: Optional[str] = None) -> World:
        """写入或更新 worlds 表中的世界观记录。"""
        payload = json.dumps(world.model_dump(mode="json"), ensure_ascii=False)
        updated_at = str(world.updated_at)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO worlds (id, owner_user_id, name, updated_at, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    owner_user_id = COALESCE(excluded.owner_user_id, worlds.owner_user_id),
                    name = excluded.name,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (world.id, owner_user_id, world.name, updated_at, payload),
            )
            conn.commit()
        return world

    def get(self, world_id: str, owner_user_id: Optional[str] = None) -> Optional[World]:
        """按 ID 查询 worlds 表中的单条记录。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT payload FROM worlds WHERE id = ?", (world_id,))
            else:
                cursor.execute(
                    "SELECT payload FROM worlds WHERE id = ? AND owner_user_id = ?",
                    (world_id, owner_user_id),
                )
            row = cursor.fetchone()
        if not row:
            return None
        return World(**json.loads(row[0]))

    def list_all(self, owner_user_id: Optional[str] = None) -> List[World]:
        """按更新时间倒序查询全部世界观记录。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT payload FROM worlds ORDER BY updated_at DESC")
            else:
                cursor.execute(
                    "SELECT payload FROM worlds WHERE owner_user_id = ? ORDER BY updated_at DESC",
                    (owner_user_id,),
                )
            rows = cursor.fetchall()
        return [World(**json.loads(row[0])) for row in rows]

    def delete(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除 worlds 表记录并返回删除结果。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
            else:
                cursor.execute(
                    "DELETE FROM worlds WHERE id = ? AND owner_user_id = ?",
                    (world_id, owner_user_id),
                )
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def exists(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """判断 worlds 表中是否存在指定 ID。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT 1 FROM worlds WHERE id = ? LIMIT 1", (world_id,))
            else:
                cursor.execute(
                    "SELECT 1 FROM worlds WHERE id = ? AND owner_user_id = ? LIMIT 1",
                    (world_id, owner_user_id),
                )
            return cursor.fetchone() is not None

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """统计 worlds 表中的记录总数。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT COUNT(1) FROM worlds")
            else:
                cursor.execute("SELECT COUNT(1) FROM worlds WHERE owner_user_id = ?", (owner_user_id,))
            row = cursor.fetchone()
        return int(row[0]) if row else 0
