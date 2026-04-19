"""故事生成执行应用用例。"""

from __future__ import annotations

from typing import Optional

from application.ports import StoryGenerationExecutor
from models.story import StoryGenerationRequest, StoryGenerationResponse


async def execute_story_generation(
    *,
    executor: StoryGenerationExecutor,
    request: StoryGenerationRequest,
    user_id: Optional[str],
) -> StoryGenerationResponse:
    """执行业务生成并返回内部响应。"""
    return await executor.generate_story(request, user_id=user_id)
