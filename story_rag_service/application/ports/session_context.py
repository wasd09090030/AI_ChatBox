"""故事会话上下文端口。"""

from __future__ import annotations

from typing import Any, Protocol

from models.story import StoryContext


class SessionContextStore(Protocol):
    """统一抽象故事会话上下文的读取与回写。"""

    def get_or_create_session(self, session_id: str, **kwargs: Any) -> StoryContext:
        """读取或创建会话上下文。"""

    def update_session(self, session_id: str, context: StoryContext) -> None:
        """回写会话上下文。"""
