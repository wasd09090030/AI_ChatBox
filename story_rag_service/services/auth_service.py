"""账号密码认证与浏览器会话服务。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    from pwdlib import PasswordHash as PwdlibPasswordHash
except ImportError:  # pragma: no cover - optional dependency
    PwdlibPasswordHash = None

from config import settings
from models.user import User
from repositories.auth_session_repository import AuthSessionRecord, SqliteAuthSessionRepository
from services.user_manager import UserManager


def _normalize_login_identifier(value: str) -> str:
    return (value or "").strip().lower()


class _PasswordHasher:
    """统一封装密码哈希，优先使用 pwdlib，缺失时回退到 PBKDF2。"""

    _PBKDF2_PREFIX = "pbkdf2_sha256"
    _PBKDF2_ITERATIONS = 390000
    _PBKDF2_SALT_BYTES = 16

    def __init__(self) -> None:
        self._pwdlib = PwdlibPasswordHash.recommended() if PwdlibPasswordHash is not None else None

    def hash(self, plain_password: str) -> str:
        if self._pwdlib is not None:
            return self._pwdlib.hash(plain_password)

        salt = secrets.token_bytes(self._PBKDF2_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            self._PBKDF2_ITERATIONS,
        )
        salt_b64 = urlsafe_b64encode(salt).decode("ascii")
        digest_b64 = urlsafe_b64encode(digest).decode("ascii")
        return f"{self._PBKDF2_PREFIX}${self._PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        if password_hash.startswith(f"{self._PBKDF2_PREFIX}$"):
            return self._verify_pbkdf2(plain_password, password_hash)
        if self._pwdlib is not None:
            try:
                return bool(self._pwdlib.verify(plain_password, password_hash))
            except Exception:
                return False
        return False

    def _verify_pbkdf2(self, plain_password: str, password_hash: str) -> bool:
        try:
            _, iterations_raw, salt_b64, digest_b64 = password_hash.split("$", 3)
            iterations = int(iterations_raw)
            salt = urlsafe_b64decode(salt_b64.encode("ascii"))
            expected_digest = urlsafe_b64decode(digest_b64.encode("ascii"))
        except Exception:
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual_digest, expected_digest)


class AuthService:
    """封装账户注册、登录与 Cookie 会话解析。"""

    def __init__(
        self,
        *,
        user_manager: UserManager,
        session_repository: SqliteAuthSessionRepository,
    ) -> None:
        self.user_manager = user_manager
        self.session_repository = session_repository
        self.password_hasher = _PasswordHasher()
        self._dummy_password_hash = self.password_hasher.hash("storybox_dummy_password")

    @staticmethod
    def hash_session_token(session_token: str) -> str:
        """对浏览器会话 token 做不可逆摘要存储。"""
        return hashlib.sha256(session_token.encode("utf-8")).hexdigest()

    def hash_password(self, plain_password: str) -> str:
        """生成密码哈希。"""
        return self.password_hasher.hash(plain_password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """校验密码。"""
        return self.password_hasher.verify(plain_password, password_hash)

    def register_user(
        self,
        *,
        login_identifier: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> User:
        """注册正式账号。"""
        normalized = _normalize_login_identifier(login_identifier)
        if len(password or "") < 8:
            raise ValueError("password must be at least 8 characters")
        password_hash = self.hash_password(password)
        return self.user_manager.create_account(
            login_identifier=normalized,
            password_hash=password_hash,
            display_name=display_name,
        )

    def authenticate_user(self, *, login_identifier: str, password: str) -> Optional[User]:
        """校验登录凭证。"""
        normalized = _normalize_login_identifier(login_identifier)
        user = self.user_manager.get_user_by_login_identifier(normalized)
        if user is None or not user.password_hash:
            self.verify_password(password, self._dummy_password_hash)
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        if user.status != "active":
            raise ValueError("user is inactive")
        return user

    def create_session(
        self,
        *,
        user_id: str,
        created_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """为用户创建浏览器会话并返回原始 cookie token。"""
        session_token = secrets.token_urlsafe(32)
        session_record = AuthSessionRecord(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            session_token_hash=self.hash_session_token(session_token),
            expires_at=datetime.utcnow() + timedelta(hours=settings.auth_session_ttl_hours),
            created_ip=(created_ip or "").strip() or None,
            user_agent=(user_agent or "").strip()[:512] or None,
        )
        self.session_repository.create_session(session_record)
        self.user_manager.update_last_login(user_id)
        return session_token

    def get_user_from_session_token(self, session_token: str) -> Optional[User]:
        """根据 Cookie token 解析当前登录用户。"""
        if not session_token:
            return None
        self.session_repository.revoke_expired_sessions()
        record = self.session_repository.get_active_by_token_hash(self.hash_session_token(session_token))
        if record is None:
            return None
        if record.expires_at <= datetime.utcnow():
            self.session_repository.revoke_by_token_hash(record.session_token_hash)
            return None
        self.session_repository.touch_session(record.session_id)
        return self.user_manager.get_user(record.user_id)

    def revoke_session(self, session_token: str) -> bool:
        """撤销当前浏览器会话。"""
        if not session_token:
            return False
        return self.session_repository.revoke_by_token_hash(self.hash_session_token(session_token))

    def claim_legacy_user_data(
        self,
        *,
        current_user_id: str,
        legacy_user_id: str,
        claim_unowned_data: bool = False,
    ) -> dict[str, Any]:
        """保守认领旧匿名用户数据。

        仅迁移能明确证明属于 legacy_user_id 的资源，不自动认领 owner 为空的数据。
        """
        normalized_legacy_user_id = (legacy_user_id or "").strip()
        result: dict[str, Any] = {
            "success": True,
            "migrated_user_settings": False,
            "migrated_worlds": 0,
            "migrated_stories": 0,
            "migrated_script_designs": 0,
            "migrated_story_sessions": 0,
            "migrated_lorebook_entries": 0,
            "migrated_runtime_states": 0,
            "migrated_memory_events": 0,
            "migrated_entity_events": 0,
            "claimed_unowned_resources": False,
            "warnings": [],
        }
        if not normalized_legacy_user_id:
            result["success"] = False
            result["warnings"].append("legacy_user_id is required")
            return result
        if normalized_legacy_user_id == current_user_id:
            result["warnings"].append("Legacy user id already matches the current account.")
            return result

        with sqlite3.connect(settings.database_path) as conn:
            conn.row_factory = sqlite3.Row

            story_ids = self._list_owned_ids(conn, "stories", "id", normalized_legacy_user_id)
            session_ids = self._list_owned_ids(conn, "story_sessions", "session_id", normalized_legacy_user_id)

            result["migrated_user_settings"] = self._claim_user_settings(
                conn,
                legacy_user_id=normalized_legacy_user_id,
                current_user_id=current_user_id,
            )
            result["migrated_worlds"] = self._reassign_owner(
                conn,
                "worlds",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            result["migrated_stories"] = self._reassign_owner(
                conn,
                "stories",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            result["migrated_script_designs"] = self._reassign_owner(
                conn,
                "script_designs",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            result["migrated_story_sessions"] = self._reassign_owner(
                conn,
                "story_sessions",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            result["migrated_lorebook_entries"] = self._reassign_owner(
                conn,
                "lorebook_entries",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            result["migrated_runtime_states"] = self._reassign_owner(
                conn,
                "story_runtime_states",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )

            # Secondary resources rely on explicit owner columns or parent-chain ownership.
            self._reassign_owner(
                conn,
                "story_session_messages",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            self._reassign_owner(
                conn,
                "persona_profiles",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )
            self._reassign_owner(
                conn,
                "story_states",
                current_user_id=current_user_id,
                legacy_user_id=normalized_legacy_user_id,
            )

            result["migrated_memory_events"] = self._count_rows_for_ids(
                conn,
                "memory_update_journal",
                "session_id",
                session_ids,
            )
            result["migrated_entity_events"] = self._count_entity_events(
                conn,
                story_ids=story_ids,
                session_ids=session_ids,
            )

            if claim_unowned_data and settings.auth_claim_unowned_enabled:
                result["warnings"].append(
                    "Unowned resources were not claimed automatically in conservative mode.",
                )
            conn.commit()

        return result

    def _claim_user_settings(
        self,
        conn: sqlite3.Connection,
        *,
        legacy_user_id: str,
        current_user_id: str,
    ) -> bool:
        if not self._table_exists(conn, "user_settings"):
            return False
        legacy_row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (legacy_user_id,),
        ).fetchone()
        if legacy_row is None:
            return False

        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (current_user_id,),
        )
        current_row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (current_user_id,),
        ).fetchone()
        if current_row is None:
            return False

        default_map: dict[str, Any] = {
            "theme": "system",
            "default_provider": "deepseek",
            "default_model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 2000,
            "story_generation_provider": None,
            "story_generation_model": None,
            "input_enhancement_provider": None,
            "input_enhancement_model": None,
            "story_adjustment_provider": None,
            "story_adjustment_model": None,
            "openai_api_key": None,
            "anthropic_api_key": None,
            "deepseek_api_key": None,
            "qwen_api_key": None,
            "gemini_api_key": None,
            "custom_api_key": None,
            "openai_base_url": None,
            "deepseek_base_url": None,
            "qwen_base_url": None,
            "gemini_base_url": None,
            "anthropic_base_url": None,
            "custom_base_url": None,
        }

        updates: dict[str, Any] = {}
        for column, default_value in default_map.items():
            if column not in legacy_row.keys() or column not in current_row.keys():
                continue
            legacy_value = legacy_row[column]
            current_value = current_row[column]
            if legacy_value is None:
                continue
            if current_value is None or current_value == default_value:
                if legacy_value != default_value:
                    updates[column] = legacy_value

        if not updates:
            return False

        assignments = ", ".join(f"{column} = ?" for column in updates)
        params = list(updates.values()) + [current_user_id]
        conn.execute(
            f"UPDATE user_settings SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            params,
        )
        conn.execute(
            "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (current_user_id,),
        )
        return True

    def _list_owned_ids(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        id_column: str,
        legacy_user_id: str,
    ) -> list[str]:
        if not self._table_has_columns(conn, table_name, {id_column, "owner_user_id"}):
            return []
        rows = conn.execute(
            f"SELECT {id_column} FROM {table_name} WHERE owner_user_id = ?",
            (legacy_user_id,),
        ).fetchall()
        return [str(row[id_column]) for row in rows if row[id_column]]

    def _reassign_owner(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        *,
        current_user_id: str,
        legacy_user_id: str,
    ) -> int:
        if not self._table_has_columns(conn, table_name, {"owner_user_id"}):
            return 0
        cursor = conn.execute(
            f"UPDATE {table_name} SET owner_user_id = ? WHERE owner_user_id = ?",
            (current_user_id, legacy_user_id),
        )
        return max(cursor.rowcount, 0)

    def _count_rows_for_ids(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        values: list[str],
    ) -> int:
        if not values or not self._table_has_columns(conn, table_name, {column_name}):
            return 0
        placeholders = ", ".join("?" for _ in values)
        row = conn.execute(
            f"SELECT COUNT(1) AS total FROM {table_name} WHERE {column_name} IN ({placeholders})",
            values,
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def _count_entity_events(
        self,
        conn: sqlite3.Connection,
        *,
        story_ids: list[str],
        session_ids: list[str],
    ) -> int:
        if not self._table_exists(conn, "entity_state_events"):
            return 0
        conditions: list[str] = []
        params: list[str] = []
        columns = self._get_table_columns(conn, "entity_state_events")
        if story_ids and "story_id" in columns:
            conditions.append(f"story_id IN ({', '.join('?' for _ in story_ids)})")
            params.extend(story_ids)
        if session_ids and "session_id" in columns:
            conditions.append(f"session_id IN ({', '.join('?' for _ in session_ids)})")
            params.extend(session_ids)
        if not conditions:
            return 0
        row = conn.execute(
            f"SELECT COUNT(1) AS total FROM entity_state_events WHERE {' OR '.join(conditions)}",
            params,
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None

    def _get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        if not self._table_exists(conn, table_name):
            return set()
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    def _table_has_columns(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        columns: set[str],
    ) -> bool:
        return columns.issubset(self._get_table_columns(conn, table_name))
