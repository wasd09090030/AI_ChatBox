"""
AI 代理服务门面。
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from .provider_registry import PROVIDER_REGISTRY, _resolve_base_url
from .streamers import stream_anthropic, stream_openai_compat


class AIProxyService:
    """
    AI API 代理服务。

    根据 provider 配置选择对应协议流式处理器，并从 UserManager 读取用户密钥与自定义地址。
    """

    def __init__(self, user_manager):
        """注入用户配置管理器（密钥与自定义 Base URL 来源）。"""
        self.user_manager = user_manager

    async def stream_chat(
        self,
        user_id: str,
        provider: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        base_url: Optional[str] = None,
        usage_sink: Optional[Dict[str, int]] = None,
    ) -> AsyncGenerator[str, None]:
        """统一流式聊天入口。

        处理步骤：
        1. 校验 provider 是否受支持；
        2. 读取用户密钥与 Base URL 覆盖；
        3. 按协议分发到对应 streamer；
        4. 将增量文本透传给上游。
        """
        if provider not in PROVIDER_REGISTRY:
            raise ValueError(
                f"Unsupported provider: '{provider}'. "
                f"Supported: {list(PROVIDER_REGISTRY)}"
            )

        cfg = PROVIDER_REGISTRY[provider]
        api_key = self.user_manager.get_decrypted_api_key(user_id, provider)
        if not api_key:
            raise ValueError(
                f"{cfg.name} API key not found. "
                f"Please configure it in Settings (provider='{provider}')."
            )

        user_base_url = self.user_manager.get_base_url(user_id, provider)
        resolved_base_url = _resolve_base_url(cfg, user_base_url, base_url)

        if cfg.protocol == "openai_compat":
            async for chunk in stream_openai_compat(
                api_key=api_key,
                base_url=resolved_base_url,
                chat_path=cfg.chat_path,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                usage_sink=usage_sink,
            ):
                yield chunk
            return

        if cfg.protocol == "anthropic":
            async for chunk in stream_anthropic(
                api_key=api_key,
                base_url=resolved_base_url,
                chat_path=cfg.chat_path,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                usage_sink=usage_sink,
            ):
                yield chunk
            return

        raise ValueError(f"Unknown protocol: {cfg.protocol}")

    def get_providers_info(self, user_id: str) -> List[Dict]:
        """返回提供商可用性视图（含用户维度密钥/地址配置状态）。"""
        result = []
        for key, cfg in PROVIDER_REGISTRY.items():
            api_key = self.user_manager.get_decrypted_api_key(user_id, key)
            user_base_url = self.user_manager.get_base_url(user_id, key)
            result.append(
                {
                    "provider": key,
                    "name": cfg.name,
                    "available": bool(api_key),
                    "models": cfg.models,
                    "default_base_url": cfg.default_base_url,
                    "custom_base_url": user_base_url or "",
                    "protocol": cfg.protocol,
                }
            )
        return result
