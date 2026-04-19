"""特性开关端口。"""

from __future__ import annotations

from typing import Optional, Protocol


class FeatureFlagReader(Protocol):
    """读取 feature flag 的最小抽象。"""

    def is_enabled(
        self,
        flag_name: str,
        *,
        user_id: Optional[str] = None,
        default: bool = False,
    ) -> bool:
        """返回指定开关是否开启。"""

