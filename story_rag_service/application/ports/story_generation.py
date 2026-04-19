"""故事生成执行端口。"""

from __future__ import annotations

from typing import Optional, Protocol

from models.story import StoryGenerationRequest, StoryGenerationResponse


class StoryGenerationExecutor(Protocol):
    """统一抽象故事生成执行入口。"""

    async def generate_story(
        self,
        request: StoryGenerationRequest,
        user_id: Optional[str] = None,
    ) -> StoryGenerationResponse:
        """执行一次非流式故事生成。"""
