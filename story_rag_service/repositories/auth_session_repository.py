"""认证会话仓储（SQLite 实现）。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.database import Database


@dataclass
class AuthSessionRecord:
    """认证会话记录。"""

    session_id: str
    user_id: str
    session_token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class SqliteAuthSessionRepository:
    """认证会话仓储。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Database(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_session(self, record: AuthSessionRecord) -> AuthSessionRecord:
        """写入会话记录。"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (
                    session_id,
                    user_id,
                    session_token_hash,
                    expires_at,
                    revoked_at,
                    created_ip,
                    user_agent,
                    created_at,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    record.session_id,
                    record.user_id,
                    record.session_token_hash,
                    record.expires_at.isoformat(),
                    record.revoked_at.isoformat() if record.revoked_at else None,
                    record.created_ip,
                    record.user_agent,
                ),
            )
            conn.commit()
        return self.get_by_session_id(record.session_id) or record

    def get_active_by_token_hash(self, session_token_hash: str) -> Optional[AuthSessionRecord]:
        """按 token hash 查询未撤销会话。"""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM auth_sessions
                WHERE session_token_hash = ?
                  AND revoked_at IS NULL
                LIMIT 1
                """,
                (session_token_hash,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_session_id(self, session_id: str) -> Optional[AuthSessionRecord]:
        """按 session_id 查询会话。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM auth_sessions WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def touch_session(self, session_id: str) -> None:
        """刷新最后访问时间。"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE auth_sessions
                SET last_seen_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (session_id,),
            )
            conn.commit()

    def revoke_by_token_hash(self, session_token_hash: str) -> bool:
        """撤销会话。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE session_token_hash = ?
                  AND revoked_at IS NULL
                """,
                (session_token_hash,),
            )
            conn.commit()
        return cursor.rowcount > 0

    def revoke_expired_sessions(self) -> int:
        """将已过期会话标记为撤销。"""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE revoked_at IS NULL
                  AND expires_at <= ?
                """,
                (now,),
            )
            conn.commit()
        return int(cursor.rowcount)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> AuthSessionRecord:
        return AuthSessionRecord(
            session_id=row["session_id"],
            user_id=row["user_id"],
            session_token_hash=row["session_token_hash"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
            created_ip=row["created_ip"],
            user_agent=row["user_agent"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
        )
