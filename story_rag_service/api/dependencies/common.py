"""通用 API 依赖提供器。"""

from __future__ import annotations

from fastapi import Request

from bootstrap.container import ServiceContainer, get_container


def get_service_container() -> ServiceContainer:
    """返回当前服务容器。"""
    return get_container()


def get_request_id(request: Request) -> str:
    """读取请求上下文中的 request_id。"""
    return getattr(request.state, "request_id", "-")
