"""故事 v2 API 健康检查路由。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def v2_health_check():
    """健康检查端点（v2）。"""
    return {
        "status": "healthy",
        "api_version": "v2",
    }
