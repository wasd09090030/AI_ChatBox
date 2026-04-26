"""
V2 API router composition.
"""

from fastapi import APIRouter

from .analytics_routes import router as analytics_router
from .auth_routes import router as auth_router
from .lorebook_routes import router as lorebook_router
from .memory_routes import router as memory_router
from .provider_routes import router as provider_router
from .roleplay_routes import router as roleplay_router
from .script_design_routes import router as script_design_router
from .story import router as story_router
from .world_story_routes import router as world_story_router

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()
router.include_router(auth_router)
router.include_router(story_router)
router.include_router(world_story_router)
router.include_router(script_design_router)
router.include_router(lorebook_router)
router.include_router(roleplay_router)
router.include_router(analytics_router)
router.include_router(memory_router)
router.include_router(provider_router)

# 控制 import * 时可导出的公共符号。
__all__ = ["router"]
