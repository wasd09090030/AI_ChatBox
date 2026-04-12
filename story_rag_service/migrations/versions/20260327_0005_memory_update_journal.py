"""新增记忆更新日志表

Revision ID: 20260327_0005
Revises: 20260317_0004
Create Date: 2026-03-27 21:30:00
"""

from alembic import op
import sqlalchemy as sa

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260327_0005"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = "20260317_0004"
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
    op.create_table(
        "memory_update_journal",
        sa.Column("event_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("memory_layer", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_turn", sa.Integer(), nullable=True),
        sa.Column("memory_key", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_payload", sa.Text(), nullable=True),
        sa.Column("after_payload", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'committed'"), nullable=False),
        sa.Column("committed_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["story_sessions.session_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_memory_update_journal_session_id",
        "memory_update_journal",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "idx_memory_update_journal_committed_at",
        "memory_update_journal",
        ["committed_at"],
        unique=False,
    )


def downgrade() -> None:
    """功能：处理 downgrade。"""
    op.drop_index("idx_memory_update_journal_committed_at", table_name="memory_update_journal")
    op.drop_index("idx_memory_update_journal_session_id", table_name="memory_update_journal")
    op.drop_table("memory_update_journal")
