"""移除旧版聊天会话表

Revision ID: 20260317_0004
Revises: 20260302_0003
Create Date: 2026-03-17 00:00:00
"""

from alembic import op

# Alembic 当前迁移版本号。
revision = "20260317_0004"
# 前置迁移版本号。
down_revision = "20260302_0003"
# 分支标签，默认不使用。
branch_labels = None
# 显式依赖的其他迁移，默认不使用。
depends_on = None


def upgrade() -> None:
    """删除旧版聊天会话表与相关索引。"""
    op.execute("DROP INDEX IF EXISTS idx_messages_created_at")
    op.execute("DROP INDEX IF EXISTS idx_messages_conversation_id")
    op.execute("DROP INDEX IF EXISTS idx_conversations_created_at")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_id")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")


def downgrade() -> None:
    """重建旧版 conversations/messages 表并恢复索引。"""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            role_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"], unique=False)
    op.create_index("idx_conversations_created_at", "conversations", ["created_at"], unique=False)
    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"], unique=False)
    op.create_index("idx_messages_created_at", "messages", ["created_at"], unique=False)
