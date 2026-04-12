"""
Story v2 router composition.
"""

from fastapi import APIRouter

from .adjustment_routes import router as adjustment_router
from .generation_routes import router as generation_router
from .health_routes import router as health_router
from .session_routes import router as session_router

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()
router.include_router(adjustment_router)
router.include_router(health_router)
router.include_router(generation_router)
router.include_router(session_router)

# 控制 import * 时可导出的公共符号。
__all__ = ["router"]
