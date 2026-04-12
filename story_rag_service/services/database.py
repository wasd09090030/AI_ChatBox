"""
SQLite 数据库服务。

负责数据库初始化与连接管理。
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from datetime import datetime


class Database:
    """封装 SQLite 连接、游标上下文与基础表初始化能力。"""
    def __init__(self, db_path: str):
        """初始化数据库连接。"""
        self.db_path = db_path
        # 确保数据目录存在。
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 支持按列名访问字段。
        return conn
    
    @contextmanager
    def get_cursor(self):
        """数据库游标上下文管理器。"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def init_database(self):
        """初始化数据库表结构。"""
        with self.get_cursor() as cursor:
            # 用户表。
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 用户设置表。
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    theme TEXT DEFAULT 'system',
                    default_provider TEXT DEFAULT 'deepseek',
                    default_model TEXT DEFAULT 'deepseek-chat',
                    temperature REAL DEFAULT 0.7,
                    max_tokens INTEGER DEFAULT 2000,
                    openai_api_key TEXT,
                    anthropic_api_key TEXT,
                    deepseek_api_key TEXT,
                    qwen_api_key TEXT,
                    gemini_api_key TEXT,
                    custom_api_key TEXT,
                    openai_base_url TEXT,
                    deepseek_base_url TEXT,
                    qwen_base_url TEXT,
                    gemini_base_url TEXT,
                    anthropic_base_url TEXT,
                    custom_base_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            # 迁移旧数据库：缺失列时增量补齐。
            self._migrate_user_settings_columns(cursor)
            
            # 为 Alembic 接管前创建的旧库补齐运行期必需表。
            self._ensure_story_session_schema(cursor)
            self._ensure_lorebook_schema(cursor)
            self._ensure_memory_update_journal_schema(cursor)
            self._ensure_story_runtime_schema(cursor)
            self._ensure_entity_state_event_schema(cursor)

    def _migrate_user_settings_columns(self, cursor) -> None:
        """为 user_settings 增量补齐新列（幂等迁移）。"""
        cursor.execute("PRAGMA table_info(user_settings)")
        existing_columns = {row["name"] for row in cursor.fetchall()}

        new_columns = [
            ("default_provider", "TEXT DEFAULT 'deepseek'"),
            ("qwen_api_key", "TEXT"),
            ("gemini_api_key", "TEXT"),
            ("custom_api_key", "TEXT"),
            ("openai_base_url", "TEXT"),
            ("deepseek_base_url", "TEXT"),
            ("qwen_base_url", "TEXT"),
            ("gemini_base_url", "TEXT"),
            ("anthropic_base_url", "TEXT"),
            ("custom_base_url", "TEXT"),
            ("story_generation_provider", "TEXT"),
            ("story_generation_model", "TEXT"),
            ("input_enhancement_provider", "TEXT"),
            ("input_enhancement_model", "TEXT"),
            ("story_adjustment_provider", "TEXT"),
            ("story_adjustment_model", "TEXT"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_type}"
                )

    def _ensure_story_session_schema(self, cursor) -> None:
        """为旧数据库补齐故事会话表与索引。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_sessions (
                session_id TEXT PRIMARY KEY,
                world_id TEXT,
                character_card_id TEXT,
                persona_id TEXT,
                first_message_sent INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_session_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                token_estimate INTEGER DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES story_sessions(session_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_story_sessions_world_id
            ON story_sessions(world_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_story_sessions_last_active
            ON story_sessions(last_active_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ssm_session_id
            ON story_session_messages(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ssm_timestamp
            ON story_session_messages(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ssm_session_role_archived
            ON story_session_messages(session_id, role, archived)
        """)

    def _ensure_lorebook_schema(self, cursor) -> None:
        """为旧数据库补齐 Lorebook SQLite 真值表与索引。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lorebook_entries (
                id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                type TEXT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                keywords TEXT DEFAULT '[]',
                trigger_keywords TEXT DEFAULT '[]',
                enabled INTEGER NOT NULL DEFAULT 1,
                priority INTEGER DEFAULT 0,
                insertion_position TEXT DEFAULT 'after_char',
                probability REAL DEFAULT 1.0,
                chroma_ref TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_metadata TEXT DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lorebook_world_id
            ON lorebook_entries(world_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lorebook_world_enabled
            ON lorebook_entries(world_id, enabled)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lorebook_priority
            ON lorebook_entries(priority)
        """)

    def _ensure_memory_update_journal_schema(self, cursor) -> None:
        """创建记忆更新日志表与索引，用于事件审计。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_update_journal (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                operation_id TEXT DEFAULT NULL,
                sequence INTEGER DEFAULT NULL,
                display_kind TEXT DEFAULT NULL,
                memory_layer TEXT NOT NULL,
                action TEXT NOT NULL,
                source TEXT NOT NULL,
                source_turn INTEGER DEFAULT NULL,
                memory_key TEXT DEFAULT NULL,
                title TEXT NOT NULL,
                reason TEXT DEFAULT NULL,
                before_payload TEXT DEFAULT NULL,
                after_payload TEXT DEFAULT NULL,
                status TEXT NOT NULL DEFAULT 'committed',
                committed_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES story_sessions(session_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_update_journal_session_id
            ON memory_update_journal(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_update_journal_committed_at
            ON memory_update_journal(committed_at)
        """)
        cursor.execute("PRAGMA table_info(memory_update_journal)")
        existing_columns = {row["name"] for row in cursor.fetchall()}
        for col_name, col_type in (
            ("operation_id", "TEXT"),
            ("sequence", "INTEGER"),
            ("display_kind", "TEXT"),
        ):
            if col_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE memory_update_journal ADD COLUMN {col_name} {col_type}"
                )
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_update_journal_operation_id
            ON memory_update_journal(operation_id)
        """)

    def _ensure_entity_state_event_schema(self, cursor) -> None:
        """创建实体状态事件流表与索引。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_state_events (
                event_id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT,
                field_name TEXT NOT NULL,
                op TEXT NOT NULL,
                value_payload TEXT,
                before_payload TEXT,
                after_payload TEXT,
                evidence_text TEXT,
                source_turn INTEGER,
                source TEXT NOT NULL,
                operation_id TEXT,
                sequence INTEGER,
                confidence REAL,
                status TEXT NOT NULL DEFAULT 'committed',
                committed_at TIMESTAMP NOT NULL,
                metadata TEXT DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_state_events_story_id
            ON entity_state_events(story_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_state_events_session_id
            ON entity_state_events(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_state_events_operation_id
            ON entity_state_events(operation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_state_events_entity_id
            ON entity_state_events(entity_id)
        """)

    def _ensure_story_runtime_schema(self, cursor) -> None:
        """为严格剧本模式补齐运行态表与索引。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_runtime_states (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL UNIQUE,
                session_id TEXT NOT NULL,
                world_id TEXT DEFAULT NULL,
                script_design_id TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_story_runtime_story_id
            ON story_runtime_states(story_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_story_runtime_session_id
            ON story_runtime_states(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_story_runtime_script_design_id
            ON story_runtime_states(script_design_id)
        """)
