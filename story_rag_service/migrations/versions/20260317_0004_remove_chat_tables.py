"""移除旧版聊天会话表

Revision ID: 20260317_0004
Revises: 20260302_0003
Create Date: 2026-03-17 00:00:00
"""

from alembic import op

# 变量作用：变量 revision，用于保存 revision 相关模块级状态。
revision = "20260317_0004"
# 变量作用：变量 down_revision，用于保存 down revision 相关模块级状态。
down_revision = "20260302_0003"
# 变量作用：变量 branch_labels，用于保存 branch labels 相关模块级状态。
branch_labels = None
# 变量作用：变量 depends_on，用于保存 depends on 相关模块级状态。
depends_on = None


def upgrade() -> None:
    """功能：处理 upgrade。"""
    op.execute("DROP INDEX IF EXISTS idx_messages_created_at")
    op.execute("DROP INDEX IF EXISTS idx_messages_conversation_id")
    op.execute("DROP INDEX IF EXISTS idx_conversations_created_at")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_id")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")


def downgrade() -> None:
    """功能：处理 downgrade。"""
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
