"""故事 RAG 服务基线 schema

Revision ID: 20260217_0001
Revises: 
Create Date: 2026-02-17 19:50:00
"""

from alembic import op
import sqlalchemy as sa

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260217_0001"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = None
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("theme", sa.Text(), server_default=sa.text("'system'"), nullable=True),
        sa.Column("default_model", sa.Text(), server_default=sa.text("'gpt-3.5-turbo'"), nullable=True),
        sa.Column("temperature", sa.Float(), server_default=sa.text("0.7"), nullable=True),
        sa.Column("max_tokens", sa.Integer(), server_default=sa.text("2000"), nullable=True),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("anthropic_api_key", sa.Text(), nullable=True),
        sa.Column("deepseek_api_key", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("role_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.Text(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )

    op.create_index("idx_conversations_user_id", "conversations", ["user_id"], unique=False)
    op.create_index("idx_conversations_created_at", "conversations", ["created_at"], unique=False)
    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"], unique=False)
    op.create_index("idx_messages_created_at", "messages", ["created_at"], unique=False)

    op.create_table(
        "worlds",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )

    op.create_table(
        "stories",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("world_id", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )

    op.create_index("idx_stories_world_id", "stories", ["world_id"], unique=False)
    op.create_index("idx_stories_updated_at", "stories", ["updated_at"], unique=False)


def downgrade() -> None:
    """功能：处理 downgrade。"""
    op.drop_index("idx_stories_updated_at", table_name="stories")
    op.drop_index("idx_stories_world_id", table_name="stories")
    op.drop_table("stories")

    op.drop_table("worlds")

    op.drop_index("idx_messages_created_at", table_name="messages")
    op.drop_index("idx_messages_conversation_id", table_name="messages")
    op.drop_index("idx_conversations_created_at", table_name="conversations")
    op.drop_index("idx_conversations_user_id", table_name="conversations")

    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("user_settings")
    op.drop_table("users")
