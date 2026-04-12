"""故事 v2 API 健康检查路由。"""

from fastapi import APIRouter

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


@router.get("/health")
async def v2_health_check():
    """健康检查端点（v2）。"""
    return {
        "status": "healthy",
        "api_version": "v2",
    }
