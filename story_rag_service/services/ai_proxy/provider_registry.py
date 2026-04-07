"""
AI 提供商注册表与基础配置解析。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ProviderConfig:
    """大模型提供商静态配置。"""

    name: str
    key_name: str
    default_base_url: str
    models: List[str]
    protocol: str  # "openai_compat" | "anthropic"
    chat_path: str = "/chat/completions"


PROVIDER_REGISTRY: Dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        name="OpenAI (GPT)",
        key_name="openai",
        default_base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        protocol="openai_compat",
    ),
    "deepseek": ProviderConfig(
        name="DeepSeek",
        key_name="deepseek",
        default_base_url="https://api.deepseek.com",
        models=["deepseek-chat", "deepseek-reasoner"],
        protocol="openai_compat",
    ),
    "qwen": ProviderConfig(
        name="Qwen 通义千问",
        key_name="qwen",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
        protocol="openai_compat",
    ),
    "gemini": ProviderConfig(
        name="Google Gemini",
        key_name="gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        protocol="openai_compat",
    ),
    "anthropic": ProviderConfig(
        name="Anthropic Claude",
        key_name="anthropic",
        default_base_url="https://api.anthropic.com",
        models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        protocol="anthropic",
        chat_path="/v1/messages",
    ),
    "custom": ProviderConfig(
        name="自定义 (OpenAI 兼容)",
        key_name="custom",
        default_base_url="",  # 必须由用户配置
        models=[],
        protocol="openai_compat",
    ),
}


def _resolve_base_url(
    provider_cfg: ProviderConfig,
    user_override: Optional[str],
    request_override: Optional[str],
) -> str:
    """按优先级解析 Base URL：请求级 > 用户配置 > 默认值。"""
    url = request_override or user_override or provider_cfg.default_base_url
    if not url:
        raise ValueError(
            "provider='custom' requires a base_url. "
            "Please configure it in Settings or pass it with the request."
        )
    return url.rstrip("/")
