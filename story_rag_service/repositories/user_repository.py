"""
User repository abstractions and SQLite implementation.
"""

from datetime import datetime
from typing import Optional

from models.user import User, UserSettings, UserSettingsUpdate
from services.database import Database


class UserRepository:
    """作用：定义 UserRepository 服务对象，用于封装对应领域流程。"""
    def get_user(self, user_id: str) -> Optional[User]:
        """功能：获取用户。"""
        raise NotImplementedError

    def create_user_with_defaults(self, user_id: str) -> None:
        """功能：创建用户 with defaults。"""
        raise NotImplementedError

    def update_settings(self, user_id: str, settings_update: UserSettingsUpdate) -> bool:
        """功能：更新 settings。"""
        raise NotImplementedError

    def update_api_key(self, user_id: str, provider_column: str, encrypted_key: Optional[str]) -> None:
        """功能：更新 API key。"""
        raise NotImplementedError

    def update_base_url(self, user_id: str, base_url_column: str, base_url: Optional[str]) -> None:
        """功能：更新 base url。"""
        raise NotImplementedError

    def update_scene_model_preference(
        self,
        user_id: str,
        provider_column: str,
        model_column: str,
        provider: Optional[str],
        model: Optional[str],
    ) -> None:
        """功能：更新 scene 模型 preference。"""
        raise NotImplementedError


class SqliteUserRepository(UserRepository):
    """作用：定义 SqliteUserRepository 服务对象，用于封装对应领域流程。"""
    def __init__(self, db: Database):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.db = db

    def get_user(self, user_id: str) -> Optional[User]:
        """功能：获取用户。"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT u.user_id, u.created_at, u.updated_at,
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
                settings=settings,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def create_user_with_defaults(self, user_id: str) -> None:
        """功能：创建用户 with defaults。"""
        with self.db.get_cursor() as cursor:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))

    def update_settings(self, user_id: str, settings_update: UserSettingsUpdate) -> bool:
        """功能：更新 settings。"""
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
        """功能：更新 API key。"""
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
        """功能：更新 scene 模型 preference。"""
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
