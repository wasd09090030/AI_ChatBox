"""用户仓储抽象与 SQLite 实现。"""

from datetime import datetime
from typing import Optional

from models.user import User, UserSettings, UserSettingsUpdate
from services.database import Database


class UserRepository:
    """用户与用户设置仓储抽象接口。"""
    def get_user(self, user_id: str) -> Optional[User]:
        """查询并返回用户聚合对象。"""
        raise NotImplementedError

    def create_user_with_defaults(self, user_id: str) -> None:
        """创建用户及默认设置记录。"""
        raise NotImplementedError

    def create_account(
        self,
        *,
        user_id: str,
        login_identifier: str,
        display_name: str,
        password_hash: str,
    ) -> None:
        """创建带登录信息的正式账号。"""
        raise NotImplementedError

    def get_user_by_login_identifier(self, login_identifier: str) -> Optional[User]:
        """按登录标识查询用户。"""
        raise NotImplementedError

    def update_settings(self, user_id: str, settings_update: UserSettingsUpdate) -> bool:
        """更新用户基础设置，返回是否发生字段变更。"""
        raise NotImplementedError

    def update_api_key(self, user_id: str, provider_column: str, encrypted_key: Optional[str]) -> None:
        """更新指定 provider 的加密 API Key。"""
        raise NotImplementedError

    def update_base_url(self, user_id: str, base_url_column: str, base_url: Optional[str]) -> None:
        """更新指定 provider 的 base URL 配置。"""
        raise NotImplementedError

    def update_scene_model_preference(
        self,
        user_id: str,
        provider_column: str,
        model_column: str,
        provider: Optional[str],
        model: Optional[str],
    ) -> None:
        """更新特定场景的模型偏好（provider + model）。"""
        raise NotImplementedError

    def update_last_login(self, user_id: str) -> None:
        """刷新用户最近登录时间。"""
        raise NotImplementedError


class SqliteUserRepository(UserRepository):
    """基于 SQLite 的用户仓储实现。"""
    def __init__(self, db: Database):
        """注入数据库访问对象。"""
        self.db = db

    def get_user(self, user_id: str) -> Optional[User]:
        """联表读取用户与设置，组装 User 聚合对象。"""
        return self._fetch_one(
            """
            SELECT u.user_id, u.login_identifier, u.display_name, u.password_hash, u.status,
                   u.created_at, u.updated_at, u.last_login_at,
                   s.theme, s.default_provider, s.default_model, s.temperature, s.max_tokens,
                   s.story_generation_provider, s.story_generation_model,
                   s.input_enhancement_provider, s.input_enhancement_model,
                   s.story_adjustment_provider, s.story_adjustment_model,
                   s.openai_api_key, s.anthropic_api_key, s.deepseek_api_key,
                   s.qwen_api_key, s.gemini_api_key, s.custom_api_key,
                   s.openai_base_url, s.deepseek_base_url, s.qwen_base_url,
                   s.gemini_base_url, s.anthropic_base_url, s.custom_base_url
            FROM users u
            LEFT JOIN user_settings s ON u.user_id = s.user_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        )

    def get_user_by_login_identifier(self, login_identifier: str) -> Optional[User]:
        """按登录标识查询用户。"""
        return self._fetch_one(
            """
            SELECT u.user_id, u.login_identifier, u.display_name, u.password_hash, u.status,
                   u.created_at, u.updated_at, u.last_login_at,
                   s.theme, s.default_provider, s.default_model, s.temperature, s.max_tokens,
                   s.story_generation_provider, s.story_generation_model,
                   s.input_enhancement_provider, s.input_enhancement_model,
                   s.story_adjustment_provider, s.story_adjustment_model,
                   s.openai_api_key, s.anthropic_api_key, s.deepseek_api_key,
                   s.qwen_api_key, s.gemini_api_key, s.custom_api_key,
                   s.openai_base_url, s.deepseek_base_url, s.qwen_base_url,
                   s.gemini_base_url, s.anthropic_base_url, s.custom_base_url
            FROM users u
            LEFT JOIN user_settings s ON u.user_id = s.user_id
            WHERE u.login_identifier = ?
            """,
            (login_identifier,),
        )

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> Optional[User]:
        """执行用户查询并映射为 User 聚合。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None

            settings = UserSettings(
                theme=row["theme"] or "system",
                default_provider=row["default_provider"] or "deepseek",
                default_model=row["default_model"] or "deepseek-chat",
                temperature=row["temperature"] if row["temperature"] is not None else 0.7,
                max_tokens=row["max_tokens"] or 2000,
                story_generation_provider=row["story_generation_provider"],
                story_generation_model=row["story_generation_model"],
                input_enhancement_provider=row["input_enhancement_provider"],
                input_enhancement_model=row["input_enhancement_model"],
                story_adjustment_provider=row["story_adjustment_provider"],
                story_adjustment_model=row["story_adjustment_model"],
                openai_api_key=row["openai_api_key"],
                anthropic_api_key=row["anthropic_api_key"],
                deepseek_api_key=row["deepseek_api_key"],
                qwen_api_key=row["qwen_api_key"],
                gemini_api_key=row["gemini_api_key"],
                custom_api_key=row["custom_api_key"],
                openai_base_url=row["openai_base_url"],
                deepseek_base_url=row["deepseek_base_url"],
                qwen_base_url=row["qwen_base_url"],
                gemini_base_url=row["gemini_base_url"],
                anthropic_base_url=row["anthropic_base_url"],
                custom_base_url=row["custom_base_url"],
            )
            return User(
                id=row["user_id"],
                login_identifier=row["login_identifier"],
                display_name=row["display_name"],
                password_hash=row["password_hash"],
                status=row["status"] or "active",
                username=row["display_name"],
                settings=settings,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_login_at=datetime.fromisoformat(row["last_login_at"]) if row["last_login_at"] else None,
            )

    def create_user_with_defaults(self, user_id: str) -> None:
        """创建用户主记录与默认设置记录。"""
        with self.db.get_cursor() as cursor:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))

    def create_account(
        self,
        *,
        user_id: str,
        login_identifier: str,
        display_name: str,
        password_hash: str,
    ) -> None:
        """创建正式账号并初始化默认设置。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (user_id, login_identifier, display_name, password_hash, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (user_id, login_identifier, display_name, password_hash),
            )
            cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))

    def update_settings(self, user_id: str, settings_update: UserSettingsUpdate) -> bool:
        """按补丁字段更新用户设置。"""
        updates = []
        params = []

        if settings_update.theme is not None:
            updates.append("theme = ?")
            params.append(settings_update.theme)
        if settings_update.default_provider is not None:
            updates.append("default_provider = ?")
            params.append(settings_update.default_provider)
        if settings_update.default_model is not None:
            updates.append("default_model = ?")
            params.append(settings_update.default_model)
        if settings_update.temperature is not None:
            updates.append("temperature = ?")
            params.append(settings_update.temperature)
        if settings_update.max_tokens is not None:
            updates.append("max_tokens = ?")
            params.append(settings_update.max_tokens)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        with self.db.get_cursor() as cursor:
            query = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            cursor.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        return True

    def update_api_key(self, user_id: str, provider_column: str, encrypted_key: Optional[str]) -> None:
        """更新指定 provider 的 API Key 并刷新更新时间。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE user_settings SET {provider_column} = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (encrypted_key, user_id),
            )
            cursor.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))

    def update_base_url(self, user_id: str, base_url_column: str, base_url: Optional[str]) -> None:
        """更新 provider 级自定义 base URL（明文配置，非敏感信息）。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE user_settings SET {base_url_column} = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (base_url or None, user_id),
            )
            cursor.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))

    def update_scene_model_preference(
        self,
        user_id: str,
        provider_column: str,
        model_column: str,
        provider: Optional[str],
        model: Optional[str],
    ) -> None:
        """更新场景模型偏好并同步用户更新时间。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE user_settings
                SET {provider_column} = ?, {model_column} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (provider or None, model or None, user_id),
            )
            cursor.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))

    def update_last_login(self, user_id: str) -> None:
        """刷新用户最近登录时间。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
