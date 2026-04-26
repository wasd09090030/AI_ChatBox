"""故事会话上下文应用用例。"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from application.ports import SessionContextStore
from models.story import StoryContext


def load_or_create_story_session_context(
    *,
    session_store: SessionContextStore,
    payload: Mapping[str, Any],
    owner_user_id: Optional[str] = None,
) -> StoryContext:
    """按图输入 payload 读取或初始化会话上下文。"""
    return session_store.get_or_create_session(
        str(payload["session_id"]),
        world_id=payload.get("world_id"),
        character_card_id=payload.get("character_card_id"),
        persona_id=payload.get("persona_id"),
        owner_user_id=owner_user_id,
    )


def persist_story_session_context(
    *,
    session_store: SessionContextStore,
    session_id: str,
    updated_context: Optional[StoryContext],
    owner_user_id: Optional[str] = None,
) -> bool:
    """将更新后的上下文回写到会话存储。"""
    if updated_context is None:
        return False

    session_store.update_session(session_id, updated_context, owner_user_id=owner_user_id)
    return True
