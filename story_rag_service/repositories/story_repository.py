"""
Story repository abstractions and implementations.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.stored_story import StoredStory


class StoryRepository:
    """作用：定义 StoryRepository 服务对象，用于封装对应领域流程。"""
    def save(self, story: StoredStory) -> StoredStory:
        """功能：保存目标对象。"""
        raise NotImplementedError

    def get(self, story_id: str) -> Optional[StoredStory]:
        """功能：获取目标对象。"""
        raise NotImplementedError

    def list_all(self, world_id: Optional[str] = None) -> List[StoredStory]:
        """功能：查询并返回 all列表。"""
        raise NotImplementedError

    def delete(self, story_id: str) -> bool:
        """功能：删除目标对象。"""
        raise NotImplementedError

    def delete_by_world(self, world_id: str) -> int:
        """功能：删除 by 世界观。"""
        raise NotImplementedError

    def count(self) -> int:
        """功能：处理 count。"""
        raise NotImplementedError


class JsonStoryRepository(StoryRepository):
    """作用：定义 JsonStoryRepository 服务对象，用于封装对应领域流程。"""
    def __init__(self, storage_path: str = "./data/stories.json"):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[StoredStory]:
        """功能：加载 all。"""
        if not self.storage_path.exists():
            return []
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [StoredStory(**item) for item in data]

    def _save_all(self, stories: List[StoredStory]) -> None:
        """功能：保存 all。"""
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump([story.model_dump(mode="json") for story in stories], file, ensure_ascii=False, indent=2)

    def save(self, story: StoredStory) -> StoredStory:
        """功能：保存目标对象。"""
        stories = {item.id: item for item in self._load_all()}
        stories[story.id] = story
        self._save_all(list(stories.values()))
        return story

    def get(self, story_id: str) -> Optional[StoredStory]:
        """功能：获取目标对象。"""
        stories = {item.id: item for item in self._load_all()}
        return stories.get(story_id)

    def list_all(self, world_id: Optional[str] = None) -> List[StoredStory]:
        """功能：查询并返回 all列表。"""
        stories = self._load_all()
        if world_id:
            stories = [story for story in stories if story.world_id == world_id]
        stories.sort(key=lambda story: story.updated_at, reverse=True)
        return stories

    def delete(self, story_id: str) -> bool:
        """功能：删除目标对象。"""
        stories = self._load_all()
        original_count = len(stories)
        stories = [story for story in stories if story.id != story_id]
        if len(stories) == original_count:
            return False
        self._save_all(stories)
        return True

    def delete_by_world(self, world_id: str) -> int:
        """功能：删除 by 世界观。"""
        stories = self._load_all()
        retained = [story for story in stories if story.world_id != world_id]
        deleted_count = len(stories) - len(retained)
        if deleted_count > 0:
            self._save_all(retained)
        return deleted_count

    def count(self) -> int:
        """功能：处理 count。"""
        return len(self._load_all())


class SqliteStoryRepository(StoryRepository):
    """作用：定义 SqliteStoryRepository 服务对象，用于封装对应领域流程。"""
    def __init__(self, db_path: str = "./data/chatbox.db"):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        """功能：处理 connect。"""
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        """功能：处理 init table。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    world_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_world_id ON stories(world_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_updated_at ON stories(updated_at)")
            conn.commit()

    def save(self, story: StoredStory) -> StoredStory:
        """功能：保存目标对象。"""
        payload = json.dumps(story.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stories (id, world_id, updated_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    world_id = excluded.world_id,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (story.id, story.world_id, story.updated_at, payload),
            )
            conn.commit()
        return story

    def get(self, story_id: str) -> Optional[StoredStory]:
        """功能：获取目标对象。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM stories WHERE id = ?", (story_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return StoredStory(**json.loads(row[0]))

    def list_all(self, world_id: Optional[str] = None) -> List[StoredStory]:
        """功能：查询并返回 all列表。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if world_id:
                cursor.execute(
                    "SELECT payload FROM stories WHERE world_id = ? ORDER BY updated_at DESC",
                    (world_id,),
                )
            else:
                cursor.execute("SELECT payload FROM stories ORDER BY updated_at DESC")
            rows = cursor.fetchall()
        return [StoredStory(**json.loads(row[0])) for row in rows]

    def delete(self, story_id: str) -> bool:
        """功能：删除目标对象。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def delete_by_world(self, world_id: str) -> int:
        """功能：删除 by 世界观。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stories WHERE world_id = ?", (world_id,))
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def count(self) -> int:
        """功能：处理 count。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(1) FROM stories")
            row = cursor.fetchone()
        return int(row[0]) if row else 0
