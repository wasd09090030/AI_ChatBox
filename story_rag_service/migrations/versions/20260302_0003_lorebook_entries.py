"""以 SQLite 为真值源的知识库条目表

Revision ID: 20260302_0003
Revises: 20260302_0002
Create Date: 2026-03-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260302_0003"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = "20260302_0002"
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
    op.create_table(
        "lorebook_entries",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("world_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("trigger_keywords", sa.Text(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("enabled", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column(
            "insertion_position",
            sa.Text(),
            server_default=sa.text("'after_char'"),
            nullable=True,
        ),
        sa.Column("probability", sa.Float(), server_default=sa.text("1.0"), nullable=True),
        sa.Column("chroma_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )

    op.create_index("idx_lorebook_world_id", "lorebook_entries", ["world_id"], unique=False)
    op.create_index(
        "idx_lorebook_world_enabled",
        "lorebook_entries",
        ["world_id", "enabled"],
        unique=False,
    )
    op.create_index("idx_lorebook_priority", "lorebook_entries", ["priority"], unique=False)


def downgrade() -> None:
    """功能：处理 downgrade。"""
    op.drop_index("idx_lorebook_priority", table_name="lorebook_entries")
    op.drop_index("idx_lorebook_world_enabled", table_name="lorebook_entries")
    op.drop_index("idx_lorebook_world_id", table_name="lorebook_entries")
    op.drop_table("lorebook_entries")
