"""
AI 代理服务子模块聚合导出。
"""

from .provider_registry import PROVIDER_REGISTRY, ProviderConfig, _resolve_base_url
from .service import AIProxyService

# 控制 import * 时可导出的公共符号。
__all__ = [
    "AIProxyService",
    "ProviderConfig",
    "PROVIDER_REGISTRY",
    "_resolve_base_url",
]
