"""用户设置读取端口。"""

from __future__ import annotations

from typing import Optional, Protocol

from models.user import User


class UserSettingsReader(Protocol):
    """面向应用层暴露的用户设置读取抽象。"""

    def get_user(self, user_id: str) -> Optional[User]:
        """返回用户聚合；不存在时返回 None。"""

    def get_decrypted_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """返回指定 provider 的用户级 API Key。"""

    def get_base_url(self, user_id: str, provider: str) -> Optional[str]:
        """返回指定 provider 的用户级 base URL。"""

