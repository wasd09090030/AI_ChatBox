"""世界管理服务。"""

from typing import List, Optional
import logging

from config import settings
from models.world import World, WorldCreate, WorldUpdate
from repositories.world_repository import (
    WorldRepository,
    JsonWorldRepository,
    SqliteWorldRepository,
)

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class WorldManager:
    """管理世界设定实体。

    运行时统一使用 SQLite，JSON 仅作为可选迁移来源。
    """
    
    def __init__(self, storage_path: str = "./data/worlds.json"):
        """初始化世界管理器。"""
        storage_path = settings.worlds_json_path or storage_path
        self.primary_repo = self._create_primary_repo()
        self._migrate_if_needed(storage_path)
        logger.info(
            "WorldManager initialized (runtime_backend=%s, count=%s)",
            "sqlite",
            self.primary_repo.count(),
        )

    def _create_primary_repo(self) -> WorldRepository:
        """创建运行时主仓储（固定 SQLite）。"""
        configured_backend = (settings.storage_backend or "sqlite").lower()
        if configured_backend != "sqlite":
            logger.warning(
                "storage_backend=%s 已降级为迁移用途，运行时将强制使用 sqlite",
                configured_backend,
            )
        return SqliteWorldRepository(settings.database_path)

    def _migrate_if_needed(self, storage_path: str) -> None:
        """按配置执行 JSON -> SQLite 的一次性迁移。"""
        if not settings.storage_auto_migrate_json_to_sqlite:
            return

        if self.primary_repo.count() > 0:
            return

        source_repo = JsonWorldRepository(storage_path)
        worlds = source_repo.list_all()
        if not worlds:
            return

        for world in worlds:
            self.primary_repo.save(world)
        logger.info("Migrated %s worlds from JSON to SQLite", len(worlds))

    def create_world(self, world_create: WorldCreate, owner_user_id: Optional[str] = None) -> World:
        """创建新世界。"""
        world = World(**world_create.model_dump())
        self.primary_repo.save(world, owner_user_id=owner_user_id)

        logger.info(f"Created world: {world.name} (ID: {world.id})")
        return world
    
    def get_world(self, world_id: str, owner_user_id: Optional[str] = None) -> Optional[World]:
        """按 world_id 获取世界。"""
        return self.primary_repo.get(world_id, owner_user_id=owner_user_id)
    
    def list_worlds(self, owner_user_id: Optional[str] = None) -> List[World]:
        """列出全部世界。"""
        return self.primary_repo.list_all(owner_user_id=owner_user_id)
    
    def update_world(
        self,
        world_id: str,
        world_update: WorldUpdate,
        owner_user_id: Optional[str] = None,
    ) -> Optional[World]:
        """更新世界信息。"""
        world = self.primary_repo.get(world_id, owner_user_id=owner_user_id)
        if not world:
            return None
        
        # 仅覆盖请求中显式传入的字段。
        update_data = world_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(world, key, value)
        
        from datetime import datetime
        world.updated_at = datetime.now()
        
        self.primary_repo.save(world, owner_user_id=owner_user_id)

        logger.info(f"Updated world: {world.name} (ID: {world_id})")
        return world
    
    def delete_world(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """删除世界。"""
        world = self.primary_repo.get(world_id, owner_user_id=owner_user_id)
        if not world:
            return False

        deleted = self.primary_repo.delete(world_id, owner_user_id=owner_user_id)
        if deleted:
            logger.info(f"Deleted world: {world.name} (ID: {world_id})")
        return deleted
    
    def world_exists(self, world_id: str, owner_user_id: Optional[str] = None) -> bool:
        """判断世界是否存在。"""
        return self.primary_repo.exists(world_id, owner_user_id=owner_user_id)
