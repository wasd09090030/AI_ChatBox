"""LLMGateway 的 LangChain 基础设施实现。"""

from __future__ import annotations

from typing import Any, Optional

from application.ports import LLMGateway, UserSettingsReader
from services.story_generation.llm_factory import create_llm


class LangChainLLMGateway(LLMGateway):
    """基于现有 llm_factory 的 LLM 客户端装配网关。"""

    def __init__(self, user_settings_reader: Optional[UserSettingsReader] = None) -> None:
        self._user_settings_reader = user_settings_reader

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
        return create_llm(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            user_id=user_id,
            for_streaming=for_streaming,
            provider=provider,
            base_url=base_url,
            user_settings_reader=self._user_settings_reader,
        )
