"""
故事生成所需的 LLM 创建与 token 工具函数。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from config import settings
from services.ai_proxy_service import PROVIDER_REGISTRY, _resolve_base_url


def detect_provider(model: str) -> str:
    """根据模型名推断 provider。"""
    model_name = (model or "").strip().lower()
    if model_name.startswith("gpt") or model_name.startswith("o1") or model_name.startswith("o3"):
        return "openai"
    if model_name.startswith("claude"):
        return "anthropic"
    if model_name.startswith("deepseek"):
        return "deepseek"
    if model_name.startswith("qwen"):
        return "qwen"
    if model_name.startswith("gemini"):
        return "gemini"
    default_provider = (
        getattr(settings, "default_llm_provider", "deepseek") or "deepseek"
    ).strip().lower()
    return default_provider if default_provider in PROVIDER_REGISTRY else "deepseek"


def get_env_api_key(provider: str) -> Optional[str]:
    """读取服务端环境变量中的 provider API key。"""
    env_map = {
        "openai": getattr(settings, "openai_api_key", None),
        "anthropic": getattr(settings, "anthropic_api_key", None),
        "deepseek": getattr(settings, "deepseek_api_key", None),
        "qwen": getattr(settings, "qwen_api_key", None),
        "gemini": getattr(settings, "gemini_api_key", None),
    }
    return env_map.get(provider)


def normalize_usage(usage_obj: Any) -> Optional[Dict[str, int]]:
    """统一 usage 结构为 input/output/total 三字段。"""
    if not usage_obj or not isinstance(usage_obj, dict):
        return None
    input_tokens = int(usage_obj.get("input_tokens", usage_obj.get("prompt_tokens", 0)) or 0)
    output_tokens = int(usage_obj.get("output_tokens", usage_obj.get("completion_tokens", 0)) or 0)
    total_tokens = int(usage_obj.get("total_tokens", input_tokens + output_tokens) or 0)
    if total_tokens <= 0:
        return None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def estimate_tokens(text: str) -> int:
    """按中英文混合文本估算 token。"""
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff" or "\u3000" <= char <= "\u30ff")
    return max(1, int(cjk * 1.7 + (len(text) - cjk) * 0.25))


def create_llm(
    *,
    model: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
    user_id: Optional[str],
    for_streaming: bool,
    provider: Optional[str],
    base_url: Optional[str],
    user_manager: Any,
):
    """
    按 provider + 模型创建 LLM 客户端。

    provider 解析优先级：
    1. 请求显式指定 provider
    2. 从 model 名称推断 provider
    """
    # 请求未显式指定模型时，优先使用用户级默认模型。
    model_name = (model or "").strip()
    user = user_manager.get_user(user_id) if user_id and user_manager else None
    user_settings = getattr(user, "settings", None)
    user_default_provider = ((getattr(user_settings, "default_provider", "") if user_settings else "") or "").strip().lower()

    if not model_name and user_settings:
        model_name = (getattr(user_settings, "default_model", "") or "").strip()
    if not model_name:
        model_name = (settings.default_model or "").strip()
    if not model_name:
        raise ValueError("Model is required for story generation.")
    effective_max_tokens = max_tokens or settings.default_max_tokens

    resolved_provider = (provider or user_default_provider or detect_provider(model_name)).strip().lower()
    if resolved_provider not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Unsupported provider '{resolved_provider}'. "
            f"Supported providers: {list(PROVIDER_REGISTRY.keys())}"
        )
    provider_cfg = PROVIDER_REGISTRY[resolved_provider]

    api_key: Optional[str] = None
    if user_id and user_manager:
        api_key = user_manager.get_decrypted_api_key(user_id, resolved_provider)
    if not api_key:
        api_key = get_env_api_key(resolved_provider)
    if not api_key:
        user_hint = f" for user_id='{user_id}'" if user_id else ""
        raise ValueError(
            f"No API key found for provider '{resolved_provider}' (model: {model_name}). "
            f"Please configure it in Dashboard or server settings{user_hint}."
        )

    user_base_url: Optional[str] = None
    if user_id and user_manager:
        user_base_url = user_manager.get_base_url(user_id, resolved_provider)
    resolved_base_url = _resolve_base_url(provider_cfg, user_base_url, base_url)

    stream_kwargs: Dict[str, Any] = {}
    if for_streaming and provider_cfg.protocol == "openai_compat":
        stream_kwargs = {"stream_options": {"include_usage": True}}

    if resolved_provider == "anthropic":
        anthropic_kwargs: Dict[str, Any] = {
            "model": model_name,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "anthropic_api_key": api_key,
        }
        if resolved_base_url:
            anthropic_kwargs["anthropic_api_url"] = resolved_base_url
        return ChatAnthropic(**anthropic_kwargs)

    kwargs: Dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "max_tokens": effective_max_tokens,
        "api_key": api_key,
        **stream_kwargs,
    }
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url
    return ChatOpenAI(**kwargs)
