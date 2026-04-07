"""
兼容层：导出 AI 代理服务公共接口。

实际实现已拆分至 `services.ai_proxy.*` 子模块。
保留该文件用于兼容历史导入路径，避免调用方大规模改名。
"""

from services.ai_proxy import AIProxyService, PROVIDER_REGISTRY, ProviderConfig, _resolve_base_url

__all__ = [
    "AIProxyService",
    "ProviderConfig",
    "PROVIDER_REGISTRY",
    "_resolve_base_url",
]
