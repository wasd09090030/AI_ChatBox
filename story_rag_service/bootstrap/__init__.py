"""后端组合根与应用装配入口。"""

from .app_factory import create_app
from .container import ServiceContainer, get_container, get_services, init_services, reset_container, set_container

__all__ = [
    "create_app",
    "ServiceContainer",
    "get_container",
    "get_services",
    "init_services",
    "reset_container",
    "set_container",
]
