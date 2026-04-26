"""
用户管理服务。

通过仓储抽象统一管理用户资料、API Key、模型偏好与场景级模型配置。
"""

import base64
import logging
import uuid
from typing import Optional

from models.user import User, UserSettingsUpdate
from repositories.user_repository import SqliteUserRepository, UserRepository
from services.database import Database

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 场景名称到数据库字段对映：每个场景对应 provider/model 两列。
SCENE_MODEL_COLUMN_MAP = {
    "story_generation": ("story_generation_provider", "story_generation_model"),
    "input_enhancement": ("input_enhancement_provider", "input_enhancement_model"),
    "story_adjustment": ("story_adjustment_provider", "story_adjustment_model"),
}

# 当前允许写入的模型提供商白名单。
SUPPORTED_PROVIDERS = {
    "openai",
    "anthropic",
    "deepseek",
    "qwen",
    "gemini",
    "custom",
}


def _normalize_provider(provider: Optional[str]) -> Optional[str]:
    """标准化提供商字段：去空白、转小写、空值归一为 None。"""
    value = (provider or "").strip().lower()
    return value or None


class UserManager:
    """管理用户数据与设置。"""

    def __init__(self, db: Database):
        """
        初始化用户管理器。
        
        Args:
            db: 数据库实例。
        """
        self.repo: UserRepository = SqliteUserRepository(db)
        logger.info("UserManager initialized with repository pattern")

    def _simple_encrypt(self, text: str) -> str:
        """用 Base64 对 API Key 做简易编码（不安全，生产环境应使用正规加密）。"""
        return base64.b64encode(text.encode()).decode()
    
    def _simple_decrypt(self, text: str) -> str:
        """对 API Key 做 Base64 解码。"""
        try:
            return base64.b64decode(text.encode()).decode()
        except Exception:
            return text  # 解码失败时按原值返回。

    def get_or_create_user(self, user_id: str) -> User:
        """
        按 ID 获取用户，不存在则创建。
        
        Args:
            user_id: 用户唯一 ID。
            
        Returns:
            用户对象。
        """
        user = self.get_user(user_id)
        if user is None:
            self.repo.create_user_with_defaults(user_id)
            logger.info(f"Created new user: {user_id}")
            user = self.get_user(user_id)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """
        按 ID 获取用户。
        
        Args:
            user_id: 用户唯一 ID。
            
        Returns:
            用户对象；未找到时返回 None。
        """
        return self.repo.get_user(user_id)

    def get_user_by_login_identifier(self, login_identifier: str) -> Optional[User]:
        """按登录标识查询正式账号。"""
        normalized = (login_identifier or "").strip().lower()
        if not normalized:
            return None
        return self.repo.get_user_by_login_identifier(normalized)

    def create_account(
        self,
        *,
        login_identifier: str,
        password_hash: str,
        display_name: Optional[str] = None,
    ) -> User:
        """创建可登录账号。"""
        normalized = (login_identifier or "").strip().lower()
        if not normalized:
            raise ValueError("login_identifier is required")
        if self.get_user_by_login_identifier(normalized) is not None:
            raise ValueError("login_identifier already exists")

        account_user_id = str(uuid.uuid4())
        resolved_display_name = (display_name or normalized.split("@")[0] or "用户").strip()
        self.repo.create_account(
            user_id=account_user_id,
            login_identifier=normalized,
            display_name=resolved_display_name,
            password_hash=password_hash,
        )
        logger.info("Created new account user: %s", account_user_id)
        created = self.get_user(account_user_id)
        if created is None:
            raise RuntimeError("Failed to load created account")
        return created

    def update_last_login(self, user_id: str) -> None:
        """刷新最近登录时间。"""
        self.repo.update_last_login(user_id)

    def update_user_settings(self, user_id: str, settings_update: UserSettingsUpdate) -> User:
        """
        更新用户设置。
        
        Args:
            user_id: 用户唯一 ID。
            settings_update: 待更新设置。
            
        Returns:
            更新后的用户对象。
        """
        user = self.get_or_create_user(user_id)
        normalized_provider = _normalize_provider(settings_update.default_provider)
        if settings_update.default_provider is not None:
            if normalized_provider is None:
                raise ValueError("default_provider is required")
            if normalized_provider not in SUPPORTED_PROVIDERS:
                raise ValueError(f"Invalid default provider: {normalized_provider}")
            settings_update.default_provider = normalized_provider
        if self.repo.update_settings(user_id, settings_update):
            logger.info(f"Updated settings for user: {user_id}")

        return self.get_user(user_id)

    def update_api_key(self, user_id: str, provider: str, api_key: str) -> User:
        """
        更新用户 API Key。

        Args:
            user_id: 用户唯一 ID。
            provider: API 提供商（openai、anthropic、deepseek、qwen、gemini、custom）。
            api_key: 待存储的 API Key。

        Returns:
            更新后的用户对象。
        """
        user = self.get_or_create_user(user_id)

        # 编码后再落库保存 API Key。
        encrypted_key = self._simple_encrypt(api_key)

        column_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "deepseek": "deepseek_api_key",
            "qwen": "qwen_api_key",
            "gemini": "gemini_api_key",
            "custom": "custom_api_key",
        }

        if provider not in column_map:
            raise ValueError(f"Invalid provider: {provider}")

        self.repo.update_api_key(user_id, column_map[provider], encrypted_key)

        logger.info(f"Updated {provider} API key for user: {user_id}")
        return self.get_user(user_id)

    def get_decrypted_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """
        获取用户已解码的 API Key。

        Args:
            user_id: 用户唯一 ID。
            provider: API 提供商。

        Returns:
            解码后的 API Key；不存在时返回 None。
        """
        user = self.get_user(user_id)
        if not user:
            return None

        key_attr_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "deepseek": "deepseek_api_key",
            "qwen": "qwen_api_key",
            "gemini": "gemini_api_key",
            "custom": "custom_api_key",
        }
        attr = key_attr_map.get(provider)
        encrypted_key = getattr(user.settings, attr, None) if attr else None

        if encrypted_key:
            return self._simple_decrypt(encrypted_key)
        return None

    def get_base_url(self, user_id: str, provider: str) -> Optional[str]:
        """返回用户为指定 provider 配置的自定义 base URL，默认配置返回 None。"""
        user = self.get_user(user_id)
        if not user:
            return None

        url_attr_map = {
            "openai": "openai_base_url",
            "anthropic": "anthropic_base_url",
            "deepseek": "deepseek_base_url",
            "qwen": "qwen_base_url",
            "gemini": "gemini_base_url",
            "custom": "custom_base_url",
        }
        attr = url_attr_map.get(provider)
        return getattr(user.settings, attr, None) if attr else None

    def delete_api_key(self, user_id: str, provider: str) -> User:
        """
        删除用户 API Key。

        Args:
            user_id: 用户唯一 ID。
            provider: API 提供商。

        Returns:
            更新后的用户对象。
        """
        user = self.get_or_create_user(user_id)

        column_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "deepseek": "deepseek_api_key",
            "qwen": "qwen_api_key",
            "gemini": "gemini_api_key",
            "custom": "custom_api_key",
        }

        if provider not in column_map:
            raise ValueError(f"Invalid provider: {provider}")

        self.repo.update_api_key(user_id, column_map[provider], None)

        logger.info(f"Deleted {provider} API key for user: {user_id}")
        return self.get_user(user_id)

    def update_base_url(self, user_id: str, provider: str, base_url: str) -> User:
        """
        为 provider 保存或清除自定义 base URL。

        Args:
            user_id: 用户唯一 ID。
            provider: API 提供商键名。
            base_url: 待存储 URL；传 "" 或 None 表示恢复默认。

        Returns:
            更新后的用户对象。
        """
        self.get_or_create_user(user_id)

        url_column_map = {
            "openai": "openai_base_url",
            "anthropic": "anthropic_base_url",
            "deepseek": "deepseek_base_url",
            "qwen": "qwen_base_url",
            "gemini": "gemini_base_url",
            "custom": "custom_base_url",
        }

        if provider not in url_column_map:
            raise ValueError(f"Invalid provider: {provider}")

        self.repo.update_base_url(user_id, url_column_map[provider], base_url or None)

        logger.info(f"Updated {provider} base URL for user: {user_id}")
        return self.get_user(user_id)

    def get_scene_model_preferences(self, user_id: str) -> dict[str, dict[str, Optional[str]]]:
        """读取场景级模型偏好。

        返回结构：{scene: {provider, model}}。
        """
        user = self.get_or_create_user(user_id)
        result: dict[str, dict[str, Optional[str]]] = {}
        for scene, (provider_attr, model_attr) in SCENE_MODEL_COLUMN_MAP.items():
            result[scene] = {
                "provider": getattr(user.settings, provider_attr, None),
                "model": getattr(user.settings, model_attr, None),
            }
        return result

    def update_scene_model_preferences(
        self,
        user_id: str,
        preferences: dict[str, dict[str, Optional[str]]],
    ) -> User:
        """更新场景级模型偏好。

        校验规则：
        - scene 必须在 SCENE_MODEL_COLUMN_MAP 中；
        - provider 与 model 必须成对出现或同时为空；
        - provider 必须在 SUPPORTED_PROVIDERS 白名单中。
        """
        self.get_or_create_user(user_id)

        for scene, value in preferences.items():
            columns = SCENE_MODEL_COLUMN_MAP.get(scene)
            if columns is None:
                raise ValueError(f"Invalid scene: {scene}")

            provider = (value.get("provider") or "").strip().lower() or None
            model = (value.get("model") or "").strip() or None

            if bool(provider) != bool(model):
                raise ValueError(f"Scene '{scene}' requires provider and model to be set together")
            if provider and provider not in SUPPORTED_PROVIDERS:
                raise ValueError(f"Invalid provider for scene '{scene}': {provider}")

            self.repo.update_scene_model_preference(
                user_id,
                columns[0],
                columns[1],
                provider,
                model,
            )

        logger.info("Updated scene model preferences for user: %s", user_id)
        return self.get_user(user_id)

    def get_default_provider_selection(self, user_id: str) -> dict[str, Optional[str]]:
        """返回默认提供商与默认模型（为空时给出系统兜底值）。"""
        user = self.get_or_create_user(user_id)
        return {
            "provider": _normalize_provider(user.settings.default_provider) or "deepseek",
            "model": (user.settings.default_model or "").strip() or "deepseek-chat",
        }
