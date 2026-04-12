"""为记忆更新日志新增操作元数据

Revision ID: 20260328_0006
Revises: 20260327_0005
Create Date: 2026-03-28 11:10:00
"""

from alembic import op
import sqlalchemy as sa

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260328_0006"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = "20260327_0005"
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
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
    """功能：处理 downgrade。"""
    op.drop_index("idx_memory_update_journal_operation_id", table_name="memory_update_journal")
    op.drop_column("memory_update_journal", "display_kind")
    op.drop_column("memory_update_journal", "sequence")
    op.drop_column("memory_update_journal", "operation_id")
