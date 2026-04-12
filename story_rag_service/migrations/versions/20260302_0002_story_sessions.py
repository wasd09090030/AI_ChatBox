"""故事会话与会话消息表

Revision ID: 20260302_0002
Revises: 20260217_0001
Create Date: 2026-03-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260302_0002"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = "20260217_0001"
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
    op.create_table(
        "story_sessions",
        sa.Column("session_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("world_id", sa.Text(), nullable=True),
        sa.Column("character_card_id", sa.Text(), nullable=True),
        sa.Column("persona_id", sa.Text(), nullable=True),
        sa.Column("first_message_sent", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("last_active_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'"), nullable=True),
    )

    op.create_table(
        "story_session_messages",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            sa.Text(),
            sa.ForeignKey("story_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("token_estimate", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("archived", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    op.create_index("idx_story_sessions_world_id", "story_sessions", ["world_id"], unique=False)
    op.create_index("idx_story_sessions_last_active", "story_sessions", ["last_active_at"], unique=False)
    op.create_index("idx_ssm_session_id", "story_session_messages", ["session_id"], unique=False)
    op.create_index("idx_ssm_timestamp", "story_session_messages", ["timestamp"], unique=False)
    op.create_index(
        "idx_ssm_session_role_archived",
        "story_session_messages",
        ["session_id", "role", "archived"],
        unique=False,
    )


def downgrade() -> None:
    """功能：处理 downgrade。"""
    op.drop_index("idx_ssm_session_role_archived", table_name="story_session_messages")
    op.drop_index("idx_ssm_timestamp", table_name="story_session_messages")
    op.drop_index("idx_ssm_session_id", table_name="story_session_messages")
    op.drop_index("idx_story_sessions_last_active", table_name="story_sessions")
    op.drop_index("idx_story_sessions_world_id", table_name="story_sessions")
    op.drop_table("story_session_messages")
    op.drop_table("story_sessions")
