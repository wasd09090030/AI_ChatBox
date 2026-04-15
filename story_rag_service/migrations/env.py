"""Alembic 迁移入口。

职责：对齐项目数据库配置并驱动 offline/online 两种迁移执行模式。
"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys
from sqlalchemy import create_engine
from alembic import context

# Alembic 运行时配置对象。
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 复用应用层数据库配置，确保迁移始终指向
# 数据目录 story_rag_service/data（不受当前工作目录影响）。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings  # noqa: E402

# 迁移目标数据库绝对路径（由应用配置统一给出）。
db_path = Path(settings.database_path).resolve()
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")


def run_migrations_offline() -> None:
    """离线模式执行迁移（不建立数据库连接，输出 SQL 语句）。"""
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
    """在线模式执行迁移（建立数据库连接并直接应用变更）。"""
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
    # `alembic upgrade --sql` 等命令会走离线路径。
    run_migrations_offline()
else:
    # 常规 `alembic upgrade head` 走在线路径。
    run_migrations_online()
