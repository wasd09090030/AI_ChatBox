"""记忆更新日志仓储。

负责将 memory update 事件落到 SQLite 的 memory_update_journal，
并提供分页检索能力，供后端 API 与前端时间线消费。
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Iterable, Optional

from config import settings

from .events import finalize_memory_update_events
from .models import MemoryUpdateEvent

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 单条 before/after 载荷的序列化长度上限，超过后会以预览形式截断。
_MAX_PAYLOAD_LENGTH = 4000


def _serialize_payload(payload: Optional[dict[str, Any]]) -> Optional[str]:
    """将 before/after 结构序列化为可持久化 JSON 文本。"""
    if payload is None:
        return None

    try:
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except TypeError:
        serialized = json.dumps({"value": str(payload)}, ensure_ascii=False, sort_keys=True)

    if len(serialized) <= _MAX_PAYLOAD_LENGTH:
        return serialized

    return json.dumps(
        {
            "truncated": True,
            "preview": serialized[:_MAX_PAYLOAD_LENGTH],
            "original_length": len(serialized),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _ensure_memory_update_journal_columns(conn: sqlite3.Connection) -> None:
    """为旧库补齐 operation_id/sequence/display_kind 列与索引。"""
    try:
        rows = conn.execute("PRAGMA table_info(memory_update_journal)").fetchall()
    except Exception:
        rows = []

    existing_columns = {row[1] for row in rows}
    for column_name, column_sql in (
        ("operation_id", "TEXT"),
        ("sequence", "INTEGER"),
        ("display_kind", "TEXT"),
    ):
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE memory_update_journal ADD COLUMN {column_name} {column_sql}")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_update_journal_operation_id
        ON memory_update_journal(operation_id)
        """
    )


def persist_memory_update_events(
    events: Iterable[MemoryUpdateEvent],
    db_path: Optional[str] = None,
    *,
    operation_id: Optional[str] = None,
    sequence_start: int = 1,
) -> None:
    """批量持久化记忆事件到 memory_update_journal。"""
    # event_id/session_id 是最小可写条件，缺失则丢弃该条，避免污染日志表。
    event_list = [event for event in events if event.get("event_id") and event.get("session_id")]
    if not event_list:
        return
    finalized_events = finalize_memory_update_events(
        event_list,
        operation_id=operation_id,
        sequence_start=sequence_start,
    )

    target_path = db_path or settings.database_path
    rows = [
        (
            event["event_id"],
            event["session_id"],
            event.get("operation_id"),
            event.get("sequence"),
            event.get("display_kind"),
            event.get("memory_layer"),
            event.get("action"),
            event.get("source"),
            event.get("source_turn"),
            event.get("memory_key"),
            event.get("title"),
            event.get("reason"),
            _serialize_payload(event.get("before")),
            _serialize_payload(event.get("after")),
            event.get("status") or "committed",
            event.get("committed_at"),
        )
        for event in finalized_events
    ]

    try:
        conn = sqlite3.connect(target_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_update_journal (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    operation_id TEXT,
                    sequence INTEGER,
                    display_kind TEXT,
                    memory_layer TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_turn INTEGER,
                    memory_key TEXT,
                    title TEXT NOT NULL,
                    reason TEXT,
                    before_payload TEXT,
                    after_payload TEXT,
                    status TEXT NOT NULL DEFAULT 'committed',
                    committed_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES story_sessions(session_id) ON DELETE CASCADE
                )
                """
            )
            _ensure_memory_update_journal_columns(conn)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_update_journal_session_id
                ON memory_update_journal(session_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_update_journal_committed_at
                ON memory_update_journal(committed_at)
                """
            )
            conn.executemany(
                """
                INSERT OR REPLACE INTO memory_update_journal (
                    event_id,
                    session_id,
                    operation_id,
                    sequence,
                    display_kind,
                    memory_layer,
                    action,
                    source,
                    source_turn,
                    memory_key,
                    title,
                    reason,
                    before_payload,
                    after_payload,
                    status,
                    committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to persist memory update journal entries: %s", exc)


def _deserialize_payload(payload: Optional[str]) -> Optional[dict[str, Any]]:
    """将持久化文本还原为结构化对象，失败时保底返回可展示字典。"""
    if not payload:
        return None
    try:
        loaded = json.loads(payload)
    except Exception:
        return {"raw": payload}
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def list_memory_update_events(
    *,
    session_id: Optional[str] = None,
    world_id: Optional[str] = None,
    source: Optional[str] = None,
    memory_layer: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """按筛选条件分页查询记忆事件时间线。"""
    target_path = db_path or settings.database_path
    safe_page = max(1, int(page))
    safe_page_size = max(1, min(int(page_size), 200))
    offset = (safe_page - 1) * safe_page_size

    where_clauses: list[str] = []
    params: list[Any] = []

    if session_id:
        where_clauses.append("j.session_id = ?")
        params.append(session_id)
    if world_id:
        where_clauses.append("s.world_id = ?")
        params.append(world_id)
    if source:
        where_clauses.append("j.source = ?")
        params.append(source)
    if memory_layer:
        where_clauses.append("j.memory_layer = ?")
        params.append(memory_layer)
    if status:
        where_clauses.append("j.status = ?")
        params.append(status)
    if search:
        keyword = f"%{search.strip()}%"
        where_clauses.append(
            "(j.session_id LIKE ? OR COALESCE(s.world_id, '') LIKE ? OR j.title LIKE ? OR COALESCE(j.reason, '') LIKE ?)"
        )
        params.extend([keyword, keyword, keyword, keyword])
    if date_from:
        where_clauses.append("j.committed_at >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("j.committed_at <= ?")
        params.append(date_to)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    try:
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        try:
            total_row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM memory_update_journal j
                LEFT JOIN story_sessions s ON s.session_id = j.session_id
                {where_sql}
                """,
                params,
            ).fetchone()

            rows = conn.execute(
                f"""
                SELECT
                    j.event_id,
                    j.session_id,
                    j.operation_id,
                    j.sequence,
                    j.display_kind,
                    s.world_id,
                    j.memory_layer,
                    j.action,
                    j.source,
                    j.source_turn,
                    j.memory_key,
                    j.title,
                    j.reason,
                    j.before_payload,
                    j.after_payload,
                    j.status,
                    j.committed_at
                FROM memory_update_journal j
                LEFT JOIN story_sessions s ON s.session_id = j.session_id
                {where_sql}
                ORDER BY j.committed_at DESC, COALESCE(j.sequence, 0) DESC, j.event_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, safe_page_size, offset],
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to query memory update journal entries: %s", exc)
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
        }

    items = [
        {
            "event_id": row["event_id"],
            "session_id": row["session_id"],
            "operation_id": row["operation_id"],
            "sequence": row["sequence"],
            "display_kind": row["display_kind"],
            "world_id": row["world_id"],
            "memory_layer": row["memory_layer"],
            "action": row["action"],
            "source": row["source"],
            "source_turn": row["source_turn"],
            "memory_key": row["memory_key"],
            "title": row["title"],
            "reason": row["reason"],
            "before": _deserialize_payload(row["before_payload"]),
            "after": _deserialize_payload(row["after_payload"]),
            "status": row["status"],
            "committed_at": row["committed_at"],
        }
        for row in rows
    ]

    return {
        "items": items,
        "total": int(total_row["total"] or 0) if total_row else 0,
        "page": safe_page,
        "page_size": safe_page_size,
    }
