"""认证会话与用户级数据隔离 schema

Revision ID: 20260426_0007
Revises: 20260328_0006
Create Date: 2026-04-26 11:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260426_0007"
down_revision = "20260328_0006"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _get_columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _get_columns(table_name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if column_name in _get_columns(table_name):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if index_name not in _get_indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if index_name in _get_indexes(table_name):
        op.drop_index(index_name, table_name=table_name)


def _create_script_designs_table_if_missing() -> None:
    if _has_table("script_designs"):
        return
    op.create_table(
        "script_designs",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=True),
        sa.Column("world_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )


def _create_story_runtime_states_table_if_missing() -> None:
    if _has_table("story_runtime_states"):
        return
    op.create_table(
        "story_runtime_states",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("world_id", sa.Text(), nullable=True),
        sa.Column("script_design_id", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("story_id", name="uq_story_runtime_states_story_id"),
    )


def _create_persona_profiles_table_if_missing() -> None:
    if _has_table("persona_profiles"):
        return
    op.create_table(
        "persona_profiles",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("traits", sa.Text(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def _create_story_states_table_if_missing() -> None:
    if _has_table("story_states"):
        return
    op.create_table(
        "story_states",
        sa.Column("session_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=True),
        sa.Column("chapter", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("conflict", sa.Text(), nullable=True),
        sa.Column("clues", sa.Text(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("relationship_arcs", sa.Text(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def _create_client_storage_entries_table_if_missing() -> None:
    if _has_table("client_storage_entries"):
        return
    op.create_table(
        "client_storage_entries",
        sa.Column("owner_user_id", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), server_default=sa.text("(datetime('now'))"), nullable=True),
        sa.PrimaryKeyConstraint("owner_user_id", "storage_key", name="pk_client_storage_entries"),
    )


def upgrade() -> None:
    """补齐认证、owner 隔离与角色档案表结构。"""
    _add_column_if_missing("users", sa.Column("login_identifier", sa.Text(), nullable=True))
    _add_column_if_missing("users", sa.Column("display_name", sa.Text(), nullable=True))
    _add_column_if_missing("users", sa.Column("password_hash", sa.Text(), nullable=True))
    _add_column_if_missing(
        "users",
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=True),
    )
    _add_column_if_missing("users", sa.Column("last_login_at", sa.TIMESTAMP(), nullable=True))
    _create_index_if_missing(
        "idx_users_login_identifier",
        "users",
        ["login_identifier"],
        unique=True,
    )

    if not _has_table("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("session_id", sa.Text(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_token_hash", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("revoked_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_ip", sa.Text(), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("last_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        )
    _create_index_if_missing("idx_auth_sessions_user_id", "auth_sessions", ["user_id"])
    _create_index_if_missing("idx_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    _create_index_if_missing(
        "idx_auth_sessions_session_token_hash",
        "auth_sessions",
        ["session_token_hash"],
        unique=True,
    )

    _add_column_if_missing("worlds", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_worlds_owner_user_id", "worlds", ["owner_user_id"])

    _add_column_if_missing("stories", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_stories_owner_user_id", "stories", ["owner_user_id"])

    _create_script_designs_table_if_missing()
    _add_column_if_missing("script_designs", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_script_designs_owner_user_id", "script_designs", ["owner_user_id"])
    _create_index_if_missing("idx_script_designs_world_id", "script_designs", ["world_id"])
    _create_index_if_missing("idx_script_designs_status", "script_designs", ["status"])
    _create_index_if_missing("idx_script_designs_updated_at", "script_designs", ["updated_at"])

    _add_column_if_missing("story_sessions", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_story_sessions_owner_user_id", "story_sessions", ["owner_user_id"])

    _add_column_if_missing("story_session_messages", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_ssm_owner_user_id", "story_session_messages", ["owner_user_id"])

    _add_column_if_missing("lorebook_entries", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_lorebook_owner_user_id", "lorebook_entries", ["owner_user_id"])

    _create_story_runtime_states_table_if_missing()
    _add_column_if_missing("story_runtime_states", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_story_runtime_story_id", "story_runtime_states", ["story_id"])
    _create_index_if_missing("idx_story_runtime_owner_user_id", "story_runtime_states", ["owner_user_id"])
    _create_index_if_missing("idx_story_runtime_session_id", "story_runtime_states", ["session_id"])
    _create_index_if_missing(
        "idx_story_runtime_script_design_id",
        "story_runtime_states",
        ["script_design_id"],
    )

    _create_persona_profiles_table_if_missing()
    _add_column_if_missing("persona_profiles", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing(
        "idx_persona_profiles_owner_user_id",
        "persona_profiles",
        ["owner_user_id"],
    )

    _create_story_states_table_if_missing()
    _add_column_if_missing("story_states", sa.Column("owner_user_id", sa.Text(), nullable=True))
    _create_index_if_missing("idx_story_states_owner_user_id", "story_states", ["owner_user_id"])

    _create_client_storage_entries_table_if_missing()
    _create_index_if_missing(
        "idx_client_storage_entries_owner_updated_at",
        "client_storage_entries",
        ["owner_user_id", "updated_at"],
    )


def downgrade() -> None:
    """最佳努力回退认证与 owner 隔离字段。"""
    _drop_index_if_exists("idx_story_states_owner_user_id", "story_states")
    _drop_column_if_exists("story_states", "owner_user_id")

    _drop_index_if_exists(
        "idx_client_storage_entries_owner_updated_at",
        "client_storage_entries",
    )
    if _has_table("client_storage_entries"):
        op.drop_table("client_storage_entries")

    _drop_index_if_exists("idx_persona_profiles_owner_user_id", "persona_profiles")
    _drop_column_if_exists("persona_profiles", "owner_user_id")

    _drop_index_if_exists("idx_story_runtime_script_design_id", "story_runtime_states")
    _drop_index_if_exists("idx_story_runtime_session_id", "story_runtime_states")
    _drop_index_if_exists("idx_story_runtime_owner_user_id", "story_runtime_states")
    _drop_index_if_exists("idx_story_runtime_story_id", "story_runtime_states")
    _drop_column_if_exists("story_runtime_states", "owner_user_id")

    _drop_index_if_exists("idx_lorebook_owner_user_id", "lorebook_entries")
    _drop_column_if_exists("lorebook_entries", "owner_user_id")

    _drop_index_if_exists("idx_ssm_owner_user_id", "story_session_messages")
    _drop_column_if_exists("story_session_messages", "owner_user_id")

    _drop_index_if_exists("idx_story_sessions_owner_user_id", "story_sessions")
    _drop_column_if_exists("story_sessions", "owner_user_id")

    _drop_index_if_exists("idx_script_designs_updated_at", "script_designs")
    _drop_index_if_exists("idx_script_designs_status", "script_designs")
    _drop_index_if_exists("idx_script_designs_world_id", "script_designs")
    _drop_index_if_exists("idx_script_designs_owner_user_id", "script_designs")
    _drop_column_if_exists("script_designs", "owner_user_id")

    _drop_index_if_exists("idx_stories_owner_user_id", "stories")
    _drop_column_if_exists("stories", "owner_user_id")

    _drop_index_if_exists("idx_worlds_owner_user_id", "worlds")
    _drop_column_if_exists("worlds", "owner_user_id")

    if _has_table("auth_sessions"):
        _drop_index_if_exists("idx_auth_sessions_session_token_hash", "auth_sessions")
        _drop_index_if_exists("idx_auth_sessions_expires_at", "auth_sessions")
        _drop_index_if_exists("idx_auth_sessions_user_id", "auth_sessions")
        op.drop_table("auth_sessions")

    _drop_index_if_exists("idx_users_login_identifier", "users")
    _drop_column_if_exists("users", "last_login_at")
    _drop_column_if_exists("users", "status")
    _drop_column_if_exists("users", "password_hash")
    _drop_column_if_exists("users", "display_name")
    _drop_column_if_exists("users", "login_identifier")
