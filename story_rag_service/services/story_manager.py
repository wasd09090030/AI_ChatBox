"""故事管理服务：负责故事持久化存储。"""

from typing import List, Optional
from datetime import datetime
import logging

from config import settings
from models.stored_story import (
    StoredStory,
    StoryCreate,
    StoryUpdate,
    StoryProgressUpdate,
    StorySegment,
    StorySegmentCreate,
)
from repositories.story_repository import (
    StoryRepository,
    JsonStoryRepository,
    SqliteStoryRepository,
)

logger = logging.getLogger(__name__)


class StoryManager:
    """管理故事存储。

    运行时默认以 SQLite 为主存储，并在需要时支持 JSON -> SQLite 启动迁移。
    """
    
    def __init__(self, storage_file: str = "./data/stories.json"):
        """
        初始化StoryManager
        
        Args:
            storage_file: 存储文件路径
        """
        storage_file = settings.stories_json_path or storage_file
        self.primary_repo = self._create_primary_repo()
        self._migrate_if_needed(storage_file)

        logger.info(
            "StoryManager initialized (runtime_backend=%s, count=%s)",
            "sqlite",
            self.primary_repo.count(),
        )

    def _create_primary_repo(self) -> StoryRepository:
        """创建运行时主仓储（当前强制 SQLite）。"""
        configured_backend = (settings.storage_backend or "sqlite").lower()
        if configured_backend != "sqlite":
            logger.warning(
                "storage_backend=%s 已降级为迁移用途，运行时将强制使用 sqlite",
                configured_backend,
            )
        return SqliteStoryRepository(settings.database_path)

    def _migrate_if_needed(self, storage_file: str) -> None:
        """按配置执行一次性 JSON -> SQLite 数据迁移。"""
        if not settings.storage_auto_migrate_json_to_sqlite:
            return

        if self.primary_repo.count() > 0:
            return

        source_repo = JsonStoryRepository(storage_file)
        stories = source_repo.list_all()
        if not stories:
            return

        for story in stories:
            self.primary_repo.save(story)
        logger.info("Migrated %s stories from JSON to SQLite", len(stories))

    def create_story(self, story_data: StoryCreate, world_name: str) -> StoredStory:
        """
        创建新故事
        
        Args:
            story_data: 故事创建数据
            world_name: 世界名称
            
        Returns:
            创建的故事
        """
        story = StoredStory(
            world_id=story_data.world_id,
            world_name=world_name,
            title=story_data.title,
            metadata=story_data.metadata
        )

        self.primary_repo.save(story)
        
        logger.info(f"Created story: {story.title} (ID: {story.id})")
        return story
    
    def get_story(self, story_id: str) -> Optional[StoredStory]:
        """
        获取故事
        
        Args:
            story_id: 故事ID
            
        Returns:
            故事对象,如果不存在返回None
        """
        return self.primary_repo.get(story_id)

    def save_story(self, story: StoredStory) -> StoredStory:
        """持久化完整故事对象，并刷新更新时间。"""
        story.updated_at = datetime.now().isoformat()
        self.primary_repo.save(story)
        return story
    
    def list_stories(self, world_id: Optional[str] = None) -> List[StoredStory]:
        """
        列出故事
        
        Args:
            world_id: 如果提供,只返回该世界的故事
            
        Returns:
            故事列表
        """
        return self.primary_repo.list_all(world_id=world_id)
    
    def update_story(self, story_id: str, update_data: StoryUpdate) -> Optional[StoredStory]:
        """
        更新故事
        
        Args:
            story_id: 故事ID
            update_data: 更新数据
            
        Returns:
            更新后的故事,如果不存在返回None
        """
        story = self.primary_repo.get(story_id)
        if not story:
            return None
        
        if update_data.title is not None:
            story.title = update_data.title
        
        if update_data.metadata is not None:
            story.metadata.update(update_data.metadata)
        
        story.updated_at = datetime.now().isoformat()
        
        self.primary_repo.save(story)
        
        logger.info(f"Updated story: {story.id}")
        return story
    
    def delete_story(self, story_id: str) -> bool:
        """
        删除故事
        
        Args:
            story_id: 故事ID
            
        Returns:
            是否成功删除
        """
        deleted = self.primary_repo.delete(story_id)
        if deleted:
            logger.info(f"Deleted story: {story_id}")
        return deleted
    
    def add_segment(self, story_id: str, segment_data: StorySegmentCreate) -> Optional[StoredStory]:
        """
        添加故事片段
        
        Args:
            story_id: 故事ID
            segment_data: 片段数据
            
        Returns:
            更新后的故事,如果不存在返回None
        """
        story = self.primary_repo.get(story_id)
        if not story:
            return None
        
        segment = StorySegment(
            prompt=segment_data.prompt,
            creation_mode=segment_data.creation_mode,
            content=segment_data.content,
            retrieved_context=segment_data.retrieved_context,
            runtime_state_snapshot=segment_data.runtime_state_snapshot,
        )
        
        story.segments.append(segment)
        story.updated_at = datetime.now().isoformat()
        
        # 如果是第一个片段且标题是默认的,自动设置标题
        if len(story.segments) == 1 and story.title == "未命名故事":
            story.title = segment.prompt[:30] + ("..." if len(segment.prompt) > 30 else "")
        
        self.primary_repo.save(story)
        
        logger.info(f"Added segment to story: {story.id}")
        return story

    def remove_last_segment(self, story_id: str) -> Optional[StoredStory]:
        """删除最后一个已持久化的故事片段。"""
        story = self.primary_repo.get(story_id)
        if not story:
            return None
        if not story.segments:
            raise ValueError("No story segments found")

        story.segments.pop()
        story.updated_at = datetime.now().isoformat()
        self.primary_repo.save(story)
        logger.info("Removed last segment from story: %s", story.id)
        return story

    def update_story_segments_content(
        self,
        story_id: str,
        updates: List[object],
    ) -> Optional[StoredStory]:
        """批量更新已存在片段的正文内容。"""
        story = self.primary_repo.get(story_id)
        if not story:
            return None

        update_map = {}
        for item in updates:
            if isinstance(item, dict):
                segment_id = item.get("segment_id")
                content = item.get("content")
            else:
                segment_id = getattr(item, "segment_id", None)
                content = getattr(item, "content", None)
            if segment_id is None or content is None:
                continue
            update_map[str(segment_id)] = str(content)
        if not update_map:
            raise ValueError("No segment updates provided")

        touched_segment_ids: set[str] = set()
        for segment in story.segments:
            if segment.id not in update_map:
                continue
            segment.content = update_map[segment.id]
            touched_segment_ids.add(segment.id)

        missing_ids = sorted(set(update_map.keys()) - touched_segment_ids)
        if missing_ids:
            raise ValueError(f"Unknown segment ids: {', '.join(missing_ids)}")

        story.updated_at = datetime.now().isoformat()
        self.primary_repo.save(story)
        logger.info("Updated %d segments in story: %s", len(touched_segment_ids), story.id)
        return story

    def update_story_progress(self, story_id: str, progress_data: StoryProgressUpdate | dict) -> Optional[StoredStory]:
        """显式更新故事剧本推进状态。

        仅更新 `progress_data.model_fields_set` 中出现的字段：
        - 传入 `None` 表示删除对应 metadata 键；
        - 传入具体值表示写入/覆盖对应键。
        """
        story = self.primary_repo.get(story_id)
        if not story:
            return None

        if isinstance(progress_data, dict):
            progress_data = StoryProgressUpdate(**progress_data)

        metadata = dict(story.metadata or {})
        if "script_design_id" in progress_data.model_fields_set:
            if progress_data.script_design_id is None:
                metadata.pop("script_design_id", None)
            else:
                metadata["script_design_id"] = progress_data.script_design_id
        if "active_stage_id" in progress_data.model_fields_set:
            if progress_data.active_stage_id is None:
                metadata.pop("active_stage_id", None)
            else:
                metadata["active_stage_id"] = progress_data.active_stage_id
        if "active_event_id" in progress_data.model_fields_set:
            if progress_data.active_event_id is None:
                metadata.pop("active_event_id", None)
            else:
                metadata["active_event_id"] = progress_data.active_event_id
        if "follow_script_design" in progress_data.model_fields_set:
            if progress_data.follow_script_design is None:
                metadata.pop("follow_script_design", None)
            else:
                metadata["follow_script_design"] = progress_data.follow_script_design
        if "creation_mode" in progress_data.model_fields_set:
            if progress_data.creation_mode is None:
                metadata.pop("creation_mode", None)
            else:
                metadata["creation_mode"] = progress_data.creation_mode
        if "runtime_state_id" in progress_data.model_fields_set:
            if progress_data.runtime_state_id is None:
                metadata.pop("runtime_state_id", None)
            else:
                metadata["runtime_state_id"] = progress_data.runtime_state_id

        story.metadata = metadata
        story.updated_at = datetime.now().isoformat()
        self.primary_repo.save(story)

        logger.info(f"Updated story progress: {story.id}")
        return story
    
    def delete_stories_by_world(self, world_id: str) -> int:
        """
        删除某个世界的所有故事
        
        Args:
            world_id: 世界ID
            
        Returns:
            删除的故事数量
        """
        deleted_count = self.primary_repo.delete_by_world(world_id)
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} stories from world: {world_id}")

        return deleted_count
