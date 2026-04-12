"""
角色扮演资料库基础设施：负责 SQLite 连接与建表初始化。
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from config import settings


class RoleplaySQLiteStore:
    """封装角色扮演资料相关的 SQLite 基础操作。"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库路径并确保角色扮演表结构就绪。"""
        self.db_path = db_path or settings.database_path
        self.init_tables()

    def connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 Row 访问模式。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self) -> None:
        """初始化角色卡、人设与剧情状态三张核心表。"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS character_cards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    system_prompt TEXT DEFAULT '',
                    first_message TEXT,
                    example_messages TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS persona_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    title TEXT,
                    traits TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS story_states (
                    session_id TEXT PRIMARY KEY,
                    chapter TEXT,
                    objective TEXT,
                    conflict TEXT,
                    clues TEXT DEFAULT '[]',
                    relationship_arcs TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def parse_json(value: Optional[str], fallback: Any) -> Any:
        """安全解析 JSON 字段，异常时回退到默认值。"""
        if value is None:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback
