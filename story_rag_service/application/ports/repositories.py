"""仓储端口定义。"""

from __future__ import annotations

from typing import Any, Optional, Protocol, Sequence


class StorySessionRepositoryPort(Protocol):
    """故事会话仓储抽象。"""

    def get_session(self, session_id: str) -> Optional[Any]:
        """按会话 ID 读取会话。"""

    def create_session(
        self,
        *,
        session_id: str,
        world_id: Optional[str] = None,
        character_card_id: Optional[str] = None,
        persona_id: Optional[str] = None,
    ) -> Any:
        """创建故事会话。"""


class StoryRepositoryPort(Protocol):
    """故事仓储抽象。"""

    def get_story(self, story_id: str) -> Optional[Any]:
        """按 ID 读取故事。"""


class ScriptDesignRepositoryPort(Protocol):
    """剧本设计仓储抽象。"""

    def get_script_design(self, script_design_id: str) -> Optional[Any]:
        """按 ID 读取剧本设计。"""


class LorebookRepositoryPort(Protocol):
    """Lorebook 仓储抽象。"""

    def list_entries(self, world_id: str) -> Sequence[Any]:
        """列出指定 world 下的 lorebook 条目。"""


class EntityStateEventRepositoryPort(Protocol):
    """实体状态事件仓储抽象。"""

    def append_event(self, payload: dict[str, Any]) -> Any:
        """追加实体状态事件。"""

    def list_events(self, session_id: str, *, limit: int = 100) -> Sequence[Any]:
        """读取指定会话的实体状态事件。"""

