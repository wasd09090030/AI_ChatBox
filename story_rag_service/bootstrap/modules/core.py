"""应用基础设施装配。"""

from __future__ import annotations

from pathlib import Path

from services.database import Database
from services.user_manager import UserManager


def create_database(*, database_path: str) -> Database:
    """创建数据库实例。"""
    return Database(database_path)


def create_user_manager(*, db: Database) -> UserManager:
    """创建用户管理器。"""
    return UserManager(db=db)


def ensure_upload_directory(*, upload_dir: Path) -> Path:
    """确保上传目录存在并返回路径。"""
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir
