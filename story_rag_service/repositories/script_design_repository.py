"""剧本设计仓储的抽象与实现。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.script_design import ScriptDesign, ScriptDesignStatus


class ScriptDesignRepository:
    """剧本设计仓储抽象接口。"""
    def save(self, script_design: ScriptDesign) -> ScriptDesign:
        """新增或更新剧本设计记录，并返回最新对象。"""
        raise NotImplementedError

    def get(self, script_design_id: str) -> Optional[ScriptDesign]:
        """按剧本设计 ID 查询单条记录。"""
        raise NotImplementedError

    def list_all(
        self,
        world_id: Optional[str] = None,
        status: Optional[ScriptDesignStatus] = None,
    ) -> List[ScriptDesign]:
        """查询剧本设计列表，可按 world_id 与状态过滤。"""
        raise NotImplementedError

    def delete(self, script_design_id: str) -> bool:
        """按 ID 删除剧本设计并返回是否成功。"""
        raise NotImplementedError

    def delete_by_world(self, world_id: str) -> int:
        """删除指定世界观下的剧本设计，返回删除数量。"""
        raise NotImplementedError

    def count(self, world_id: Optional[str] = None) -> int:
        """统计剧本设计数量，可按 world_id 过滤。"""
        raise NotImplementedError


class JsonScriptDesignRepository(ScriptDesignRepository):
    """基于 JSON 文件的剧本设计仓储实现。"""
    def __init__(self, storage_path: str = "./data/script_designs.json"):
        """初始化 JSON 存储路径并确保父目录存在。"""
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[ScriptDesign]:
        """从 JSON 文件加载全部剧本设计记录。"""
        if not self.storage_path.exists():
            return []
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [ScriptDesign(**item) for item in data]

    def _save_all(self, script_designs: List[ScriptDesign]) -> None:
        """将全部剧本设计记录覆写保存到 JSON 文件。"""
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(
                [item.model_dump(mode="json") for item in script_designs],
                file,
                ensure_ascii=False,
                indent=2,
            )

    def save(self, script_design: ScriptDesign) -> ScriptDesign:
        """以 ID 为键保存剧本设计（存在则更新，不存在则新增）。"""
        items = {item.id: item for item in self._load_all()}
        items[script_design.id] = script_design
        self._save_all(list(items.values()))
        return script_design

    def get(self, script_design_id: str) -> Optional[ScriptDesign]:
        """按 ID 从 JSON 记录中查询剧本设计。"""
        items = {item.id: item for item in self._load_all()}
        return items.get(script_design_id)

    def list_all(
        self,
        world_id: Optional[str] = None,
        status: Optional[ScriptDesignStatus] = None,
    ) -> List[ScriptDesign]:
        """返回剧本设计列表，并按更新时间倒序排列。"""
        items = self._load_all()
        if world_id:
            items = [item for item in items if item.world_id == world_id]
        if status:
            items = [item for item in items if item.status == status]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def delete(self, script_design_id: str) -> bool:
        """按 ID 删除 JSON 中的剧本设计记录。"""
        items = self._load_all()
        retained = [item for item in items if item.id != script_design_id]
        if len(retained) == len(items):
            return False
        self._save_all(retained)
        return True

    def delete_by_world(self, world_id: str) -> int:
        """删除指定 world_id 下的 JSON 剧本设计记录。"""
        items = self._load_all()
        retained = [item for item in items if item.world_id != world_id]
        deleted_count = len(items) - len(retained)
        if deleted_count > 0:
            self._save_all(retained)
        return deleted_count

    def count(self, world_id: Optional[str] = None) -> int:
        """统计 JSON 存储中的剧本设计数量。"""
        return len(self.list_all(world_id=world_id))


class SqliteScriptDesignRepository(ScriptDesignRepository):
    """基于 SQLite 的剧本设计仓储实现。"""
    def __init__(self, db_path: str = "./data/chatbox.db"):
        """初始化数据库路径并确保 script_designs 表与索引可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        """创建 SQLite 连接。"""
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        """初始化 script_designs 表与查询索引。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS script_designs (
                    id TEXT PRIMARY KEY,
                    world_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_script_designs_world_id ON script_designs(world_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_script_designs_status ON script_designs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_script_designs_updated_at ON script_designs(updated_at)")
            conn.commit()

    def save(self, script_design: ScriptDesign) -> ScriptDesign:
        """写入或更新 script_designs 表中的剧本设计记录。"""
        payload = json.dumps(script_design.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO script_designs (id, world_id, status, updated_at, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    world_id = excluded.world_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    script_design.id,
                    script_design.world_id,
                    script_design.status,
                    str(script_design.updated_at),
                    payload,
                ),
            )
            conn.commit()
        return script_design

    def get(self, script_design_id: str) -> Optional[ScriptDesign]:
        """按 ID 查询 script_designs 表中的单条记录。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM script_designs WHERE id = ?", (script_design_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return ScriptDesign(**json.loads(row[0]))

    def list_all(
        self,
        world_id: Optional[str] = None,
        status: Optional[ScriptDesignStatus] = None,
    ) -> List[ScriptDesign]:
        """查询剧本设计列表，并按更新时间倒序返回。"""
        query = "SELECT payload FROM script_designs"
        clauses = []
        params = []
        if world_id:
            clauses.append("world_id = ?")
            params.append(world_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC"

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        return [ScriptDesign(**json.loads(row[0])) for row in rows]

    def delete(self, script_design_id: str) -> bool:
        """按 ID 删除 script_designs 表记录并返回结果。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_designs WHERE id = ?", (script_design_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def delete_by_world(self, world_id: str) -> int:
        """删除指定 world_id 下的剧本设计记录并返回数量。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_designs WHERE world_id = ?", (world_id,))
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def count(self, world_id: Optional[str] = None) -> int:
        """统计 script_designs 表中的记录数量。"""
        query = "SELECT COUNT(1) FROM script_designs"
        params = []
        if world_id:
            query += " WHERE world_id = ?"
            params.append(world_id)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
        return int(row[0]) if row else 0