"""故事改写相关路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies.auth import get_current_user
from api.dependencies.world import StoryAdjustmentDependencies, get_story_adjustment_dependencies
from api.v2.schemas import StoryAdjustmentPolishRequest, StoryAdjustmentPolishResponse
from models.user import User

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


@router.post("/story/adjustments/polish", response_model=StoryAdjustmentPolishResponse)
async def polish_story_selection(
    request: StoryAdjustmentPolishRequest,
    current_user: User = Depends(get_current_user),
    adjustment_services: StoryAdjustmentDependencies = Depends(get_story_adjustment_dependencies),
):
    """润色选中文本片段，不修改正式故事会话状态。"""
    try:
        payload = await adjustment_services.story_adjustment_service.polish_selection(
            request,
            user_id=current_user.id,
            owner_user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StoryAdjustmentPolishResponse(**payload)
