"""
Lorebook 的 SQLite 仓储：负责本地结构化数据持久化。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from models.lorebook import LorebookEntry
from services.database import Database


class LorebookSqliteStore:
    """提供 lorebook 条目在 SQLite 中的读写与兼容迁移能力。"""
    def __init__(self, db_path: Optional[str] = None):
        """初始化 SQLite 仓储并执行表结构兼容检查。"""
        self.db_path = db_path or settings.database_path
        Database(self.db_path)
        self.ensure_raw_metadata_column()
        self.ensure_owner_user_id_column()

    def connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用按列名读取。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_raw_metadata_column(self) -> None:
        """幂等补齐 raw_metadata 字段，避免老库缺列。"""
        try:
            with self.connect() as conn:
                conn.execute(
                    "ALTER TABLE lorebook_entries ADD COLUMN raw_metadata TEXT DEFAULT NULL"
                )
        except Exception:
            pass

    def ensure_owner_user_id_column(self) -> None:
        """幂等补齐 owner_user_id 字段。"""
        try:
            with self.connect() as conn:
                conn.execute(
                    "ALTER TABLE lorebook_entries ADD COLUMN owner_user_id TEXT DEFAULT NULL"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lorebook_owner_user_id ON lorebook_entries(owner_user_id)"
                )
        except Exception:
            try:
                with self.connect() as conn:
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_lorebook_owner_user_id ON lorebook_entries(owner_user_id)"
                    )
            except Exception:
                pass

    def upsert_entry(
        self,
        entry: LorebookEntry,
        chroma_ref: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> None:
        """写入或覆盖 lorebook 条目。

        以 entry.id 为主键，保留旧 `chroma_ref/raw_metadata` 的兜底合并语义。
        """
        keywords_json = json.dumps(entry.keywords or [], ensure_ascii=False)
        trigger_keywords_json = json.dumps(
            entry.metadata.get("trigger_keywords", []) or [], ensure_ascii=False
        )
        enabled = int(entry.metadata.get("enabled", 1))
        priority = int(entry.metadata.get("priority", entry.metadata.get("importance", 0)))
        insertion_position = entry.metadata.get("insertion_position", "after_char")
        probability = float(entry.metadata.get("probability", 1.0))
        now = datetime.now().isoformat()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO lorebook_entries
                    (id, owner_user_id, world_id, type, name, content, keywords, trigger_keywords,
                     enabled, priority, insertion_position, probability, chroma_ref,
                     raw_metadata, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    owner_user_id=COALESCE(excluded.owner_user_id, lorebook_entries.owner_user_id),
                    world_id=excluded.world_id,
                    type=excluded.type,
                    name=excluded.name,
                    content=excluded.content,
                    keywords=excluded.keywords,
                    trigger_keywords=excluded.trigger_keywords,
                    enabled=excluded.enabled,
                    priority=excluded.priority,
                    insertion_position=excluded.insertion_position,
                    probability=excluded.probability,
                    chroma_ref=COALESCE(excluded.chroma_ref, lorebook_entries.chroma_ref),
                    raw_metadata=COALESCE(excluded.raw_metadata, lorebook_entries.raw_metadata),
                    updated_at=excluded.updated_at
                """,
                (
                    entry.id,
                    owner_user_id,
                    entry.world_id,
                    str(entry.type),
                    entry.name,
                    entry.description,
                    keywords_json,
                    trigger_keywords_json,
                    enabled,
                    priority,
                    insertion_position,
                    probability,
                    chroma_ref,
                    json.dumps(entry.metadata, ensure_ascii=False, default=str) if entry.metadata else None,
                    now,
                    now,
                ),
            )

    def delete_entry(self, entry_id: str, owner_user_id: Optional[str] = None) -> None:
        """删除指定条目。"""
        with self.connect() as conn:
            if owner_user_id is None:
                conn.execute("DELETE FROM lorebook_entries WHERE id=?", (entry_id,))
            else:
                conn.execute(
                    "DELETE FROM lorebook_entries WHERE id=? AND owner_user_id=?",
                    (entry_id, owner_user_id),
                )

    def get_metadata(self, entry_id: str, owner_user_id: Optional[str] = None) -> Dict[str, Any]:
        """读取检索相关元数据（启用、优先级、插入位置、概率）。"""
        with self.connect() as conn:
            if owner_user_id is None:
                row = conn.execute(
                    "SELECT enabled, priority, insertion_position, probability "
                    "FROM lorebook_entries WHERE id=?",
                    (entry_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT enabled, priority, insertion_position, probability "
                    "FROM lorebook_entries WHERE id=? AND owner_user_id=?",
                    (entry_id, owner_user_id),
                ).fetchone()
        if row:
            return {
                "enabled": bool(row["enabled"]),
                "priority": row["priority"],
                "insertion_position": row["insertion_position"],
                "probability": row["probability"],
            }
        return {"enabled": True, "priority": 0, "insertion_position": "after_char", "probability": 1.0}

    def list_entries(
        self,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按可选 world_id 枚举条目，并合并系统/原始元数据。"""
        with self.connect() as conn:
            clauses = []
            params: list[Any] = []
            if world_id:
                clauses.append("world_id=?")
                params.append(world_id)
            if owner_user_id is not None:
                clauses.append("owner_user_id=?")
                params.append(owner_user_id)
            query = "SELECT * FROM lorebook_entries"
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            rows = conn.execute(query, tuple(params)).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            keywords = json.loads(row["keywords"] or "[]")
            trigger_keywords = json.loads(row["trigger_keywords"] or "[]")
            raw_meta_json = row["raw_metadata"] if "raw_metadata" in row.keys() else None
            raw_meta: Dict[str, Any] = json.loads(raw_meta_json) if raw_meta_json else {}
            sys_meta: Dict[str, Any] = {
                "_sqlite_id": row["id"],
                "_chroma_id": row["chroma_ref"],
                "world_id": row["world_id"],
                "owner_user_id": row["owner_user_id"] if "owner_user_id" in row.keys() else None,
                "type": row["type"],
                "name": row["name"],
                "keywords": ",".join(keywords),
                "trigger_keywords": trigger_keywords,
                "enabled": bool(row["enabled"]),
                "priority": row["priority"],
                "insertion_position": row["insertion_position"],
                "probability": row["probability"],
            }
            merged_meta = {**raw_meta, **sys_meta}
            result.append(
                {
                    "id": row["id"],
                    "world_id": row["world_id"],
                    "owner_user_id": row["owner_user_id"] if "owner_user_id" in row.keys() else None,
                    "name": row["name"],
                    "type": row["type"],
                    "description": row["content"],
                    "content": row["content"],
                    "keywords": keywords,
                    "enabled": bool(row["enabled"]),
                    "priority": row["priority"],
                    "insertion_position": row["insertion_position"],
                    "probability": row["probability"],
                    "chroma_ref": row["chroma_ref"],
                    "metadata": merged_meta,
                }
            )
        return result

    def clear_all(self) -> None:
        """清空全部 lorebook 条目。"""
        with self.connect() as conn:
            conn.execute("DELETE FROM lorebook_entries")
