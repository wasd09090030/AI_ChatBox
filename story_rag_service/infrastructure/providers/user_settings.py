"""用户设置读取端口的基础设施适配器。"""

from __future__ import annotations

from typing import Optional

from application.ports import UserSettingsReader
from models.user import User
from services.user_manager import UserManager


class UserSettingsServiceAdapter(UserSettingsReader):
    """把 UserManager 适配为应用层可消费的 UserSettingsReader。"""

    def __init__(self, user_manager: Optional[UserManager]) -> None:
        self._user_manager = user_manager

    def get_user(self, user_id: str) -> Optional[User]:
        if not self._user_manager:
            return None
        return self._user_manager.get_user(user_id)

    def get_decrypted_api_key(self, user_id: str, provider: str) -> Optional[str]:
        if not self._user_manager:
            return None
        return self._user_manager.get_decrypted_api_key(user_id, provider)

    def get_base_url(self, user_id: str, provider: str) -> Optional[str]:
        if not self._user_manager:
            return None
        return self._user_manager.get_base_url(user_id, provider)
