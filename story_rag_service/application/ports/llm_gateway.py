"""LLM 网关端口。"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class LLMGateway(Protocol):
    """统一封装 LLM 客户端装配能力。"""

    def create_client(
        self,
        *,
        model: Optional[str],
        provider: Optional[str],
        base_url: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        user_id: Optional[str],
        for_streaming: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """返回已解析 provider/model/api_key/base_url 的 LLM 客户端。"""
