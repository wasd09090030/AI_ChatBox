"""故事仓储接口与实现。

提供 JSON 与 SQLite 两种后端，统一管理故事对象的持久化与查询。
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from models.stored_story import StoredStory


class StoryRepository:
    """故事仓储抽象接口。"""
    def save(self, story: StoredStory, owner_user_id: Optional[str] = None) -> StoredStory:
        """新增或更新故事记录，并返回最新对象。"""
        raise NotImplementedError

    def get(self, story_id: str, owner_user_id: Optional[str] = None) -> Optional[StoredStory]:
        """按故事 ID 查询单条记录。"""
        raise NotImplementedError

    def list_all(self, world_id: Optional[str] = None, owner_user_id: Optional[str] = None) -> List[StoredStory]:
        """查询故事列表，可按 world_id 过滤。"""
        raise NotImplementedError

    def delete(self, story_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除故事，返回是否删除成功。"""
        raise NotImplementedError

    def delete_by_world(self, world_id: str, owner_user_id: Optional[str] = None) -> int:
        """删除指定世界观下的全部故事，返回删除数量。"""
        raise NotImplementedError

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """返回故事总数。"""
        raise NotImplementedError


class JsonStoryRepository(StoryRepository):
    """基于 JSON 文件的故事仓储实现。"""
    def __init__(self, storage_path: str = "./data/stories.json"):
        """初始化 JSON 存储路径并确保父目录存在。"""
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[StoredStory]:
        """从 JSON 文件加载全部故事记录。"""
        if not self.storage_path.exists():
            return []
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [StoredStory(**item) for item in data]

    def _save_all(self, stories: List[StoredStory]) -> None:
        """将全部故事记录覆写保存到 JSON 文件。"""
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump([story.model_dump(mode="json") for story in stories], file, ensure_ascii=False, indent=2)

    def save(self, story: StoredStory, owner_user_id: Optional[str] = None) -> StoredStory:
        """以 ID 为键保存故事（存在则更新，不存在则新增）。"""
        stories = {item.id: item for item in self._load_all()}
        stories[story.id] = story
        self._save_all(list(stories.values()))
        return story

    def get(self, story_id: str, owner_user_id: Optional[str] = None) -> Optional[StoredStory]:
        """按 ID 从 JSON 记录中查询故事。"""
        stories = {item.id: item for item in self._load_all()}
        return stories.get(story_id)

    def list_all(self, world_id: Optional[str] = None, owner_user_id: Optional[str] = None) -> List[StoredStory]:
        """返回故事列表，并按更新时间倒序排列。"""
        stories = self._load_all()
        if world_id:
            stories = [story for story in stories if story.world_id == world_id]
        stories.sort(key=lambda story: story.updated_at, reverse=True)
        return stories

    def delete(self, story_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除 JSON 中的故事记录。"""
        stories = self._load_all()
        original_count = len(stories)
        stories = [story for story in stories if story.id != story_id]
        if len(stories) == original_count:
            return False
        self._save_all(stories)
        return True

    def delete_by_world(self, world_id: str, owner_user_id: Optional[str] = None) -> int:
        """删除指定 world_id 下的 JSON 故事记录。"""
        stories = self._load_all()
        retained = [story for story in stories if story.world_id != world_id]
        deleted_count = len(stories) - len(retained)
        if deleted_count > 0:
            self._save_all(retained)
        return deleted_count

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """统计 JSON 存储中的故事数量。"""
        return len(self._load_all())


class SqliteStoryRepository(StoryRepository):
    """基于 SQLite 的故事仓储实现。"""
    def __init__(self, db_path: str = "./data/chatbox.db"):
        """初始化数据库路径并确保 stories 表和索引可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        """创建 SQLite 连接。"""
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        """初始化 stories 表与查询索引。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    owner_user_id TEXT DEFAULT NULL,
                    world_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            existing_columns = {
                row[1]
                for row in cursor.execute("PRAGMA table_info(stories)").fetchall()
            }
            if "owner_user_id" not in existing_columns:
                cursor.execute("ALTER TABLE stories ADD COLUMN owner_user_id TEXT DEFAULT NULL")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_owner_user_id ON stories(owner_user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_world_id ON stories(world_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_updated_at ON stories(updated_at)")
            conn.commit()

    def save(self, story: StoredStory, owner_user_id: Optional[str] = None) -> StoredStory:
        """写入或更新 stories 表中的故事记录。"""
        payload = json.dumps(story.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stories (id, owner_user_id, world_id, updated_at, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    owner_user_id = COALESCE(excluded.owner_user_id, stories.owner_user_id),
                    world_id = excluded.world_id,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (story.id, owner_user_id, story.world_id, story.updated_at, payload),
            )
            conn.commit()
        return story

    def get(self, story_id: str, owner_user_id: Optional[str] = None) -> Optional[StoredStory]:
        """按 ID 查询 stories 表中的单条故事。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT payload FROM stories WHERE id = ?", (story_id,))
            else:
                cursor.execute(
                    "SELECT payload FROM stories WHERE id = ? AND owner_user_id = ?",
                    (story_id, owner_user_id),
                )
            row = cursor.fetchone()
        if not row:
            return None
        return StoredStory(**json.loads(row[0]))

    def list_all(self, world_id: Optional[str] = None, owner_user_id: Optional[str] = None) -> List[StoredStory]:
        """查询故事列表，并按更新时间倒序返回。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            clauses = []
            params = []
            if world_id:
                clauses.append("world_id = ?")
                params.append(world_id)
            if owner_user_id is not None:
                clauses.append("owner_user_id = ?")
                params.append(owner_user_id)
            query = "SELECT payload FROM stories"
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY updated_at DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        return [StoredStory(**json.loads(row[0])) for row in rows]

    def delete(self, story_id: str, owner_user_id: Optional[str] = None) -> bool:
        """按 ID 删除 stories 表记录并返回结果。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            else:
                cursor.execute(
                    "DELETE FROM stories WHERE id = ? AND owner_user_id = ?",
                    (story_id, owner_user_id),
                )
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def delete_by_world(self, world_id: str, owner_user_id: Optional[str] = None) -> int:
        """删除指定 world_id 下的 stories 记录并返回数量。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("DELETE FROM stories WHERE world_id = ?", (world_id,))
            else:
                cursor.execute(
                    "DELETE FROM stories WHERE world_id = ? AND owner_user_id = ?",
                    (world_id, owner_user_id),
                )
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def count(self, owner_user_id: Optional[str] = None) -> int:
        """统计 stories 表中的记录总数。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            if owner_user_id is None:
                cursor.execute("SELECT COUNT(1) FROM stories")
            else:
                cursor.execute("SELECT COUNT(1) FROM stories WHERE owner_user_id = ?", (owner_user_id,))
            row = cursor.fetchone()
        return int(row[0]) if row else 0
