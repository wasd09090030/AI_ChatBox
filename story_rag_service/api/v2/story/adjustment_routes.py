"""故事改写相关路由。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from api.service_context import ServiceContainer, get_services
from api.v2.schemas import StoryAdjustmentPolishRequest, StoryAdjustmentPolishResponse

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


@router.post("/story/adjustments/polish", response_model=StoryAdjustmentPolishResponse)
async def polish_story_selection(
    request: StoryAdjustmentPolishRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    services: ServiceContainer = Depends(get_services),
):
    """润色选中文本片段，不修改正式故事会话状态。"""
    try:
        payload = await services.story_adjustment_service.polish_selection(request, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StoryAdjustmentPolishResponse(**payload)
