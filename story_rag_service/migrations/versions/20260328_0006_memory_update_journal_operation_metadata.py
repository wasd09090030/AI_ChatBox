"""为记忆更新日志新增操作元数据

Revision ID: 20260328_0006
Revises: 20260327_0005
Create Date: 2026-03-28 11:10:00
"""

from alembic import op
import sqlalchemy as sa

# Alembic 当前迁移版本号。
revision = "20260328_0006"
# 前置迁移版本号。
down_revision = "20260327_0005"
# 分支标签，默认不使用。
branch_labels = None
# 显式依赖的其他迁移，默认不使用。
depends_on = None


def upgrade() -> None:
    """为记忆日志补充 operation/sequence/display 元数据字段。"""
    op.add_column("memory_update_journal", sa.Column("operation_id", sa.Text(), nullable=True))
    op.add_column("memory_update_journal", sa.Column("sequence", sa.Integer(), nullable=True))
    op.add_column("memory_update_journal", sa.Column("display_kind", sa.Text(), nullable=True))
    op.create_index(
        "idx_memory_update_journal_operation_id",
        "memory_update_journal",
        ["operation_id"],
        unique=False,
    )


def downgrade() -> None:
    """移除 operation 相关元数据字段并删除索引。"""
    op.drop_index("idx_memory_update_journal_operation_id", table_name="memory_update_journal")
    op.drop_column("memory_update_journal", "display_kind")
    op.drop_column("memory_update_journal", "sequence")
    op.drop_column("memory_update_journal", "operation_id")
