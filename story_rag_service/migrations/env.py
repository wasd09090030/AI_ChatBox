"""文件说明：项目文件 env.py 的核心逻辑实现。"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys
from sqlalchemy import create_engine
from alembic import context

# 变量 config，用于保存配置相关模块级状态。
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 复用应用层数据库配置，确保迁移始终指向
# 数据目录 story_rag_service/data（不受当前工作目录影响）。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings  # noqa: E402

# 路径变量 db_path，用于定位文件系统资源。
db_path = Path(settings.database_path).resolve()
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")


def run_migrations_offline() -> None:
    """功能：执行 migrations offline。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """功能：执行 migrations online。"""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
