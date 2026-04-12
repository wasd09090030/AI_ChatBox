"""实体状态事件流仓储（SQLite 实现）。

负责事件追加、查询和回放前筛选所需的删除能力。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, List, Sequence

from models.entity_state_event import EntityStateEventRecord


def _serialize_payload(value: Any) -> str | None:
    """将 Python 对象序列化为 JSON 字符串。"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _deserialize_payload(value: str | None) -> Any:
    """将 JSON 字符串还原为 Python 对象。"""
    if value is None or value == "":
        return None
    return json.loads(value)


class SqliteEntityStateEventRepository:
    """实体状态事件流仓储。"""

    def __init__(self, db_path: str):
        """初始化数据库路径并确保事件表结构可用。"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用 Row 访问模式。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        """初始化事件表与回放所需索引。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS entity_state_events (
                    event_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_name TEXT,
                    field_name TEXT NOT NULL,
                    op TEXT NOT NULL,
                    value_payload TEXT,
                    before_payload TEXT,
                    after_payload TEXT,
                    evidence_text TEXT,
                    source_turn INTEGER,
                    source TEXT NOT NULL,
                    operation_id TEXT,
                    sequence INTEGER,
                    confidence REAL,
                    status TEXT NOT NULL DEFAULT 'committed',
                    committed_at TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_state_events_story_id
                ON entity_state_events(story_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_state_events_session_id
                ON entity_state_events(session_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_state_events_operation_id
                ON entity_state_events(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_state_events_entity_id
                ON entity_state_events(entity_id)
                """
            )
            conn.commit()

    def append_events(self, events: Sequence[EntityStateEventRecord]) -> List[EntityStateEventRecord]:
        """批量追加事件记录（按 event_id 幂等覆盖）。"""
        if not events:
            return []

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO entity_state_events (
                    event_id,
                    story_id,
                    session_id,
                    entity_id,
                    entity_type,
                    entity_name,
                    field_name,
                    op,
                    value_payload,
                    before_payload,
                    after_payload,
                    evidence_text,
                    source_turn,
                    source,
                    operation_id,
                    sequence,
                    confidence,
                    status,
                    committed_at,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.event_id,
                        event.story_id,
                        event.session_id,
                        event.entity_id,
                        event.entity_type,
                        event.entity_name,
                        event.field_name,
                        event.op,
                        _serialize_payload(event.value),
                        _serialize_payload(event.before),
                        _serialize_payload(event.after),
                        event.evidence_text,
                        event.source_turn,
                        event.source,
                        event.operation_id,
                        event.sequence,
                        event.confidence,
                        event.status,
                        event.committed_at.isoformat(),
                        _serialize_payload(event.metadata),
                    )
                    for event in events
                ],
            )
            conn.commit()
        return list(events)

    def list_by_story_id(self, story_id: str) -> List[EntityStateEventRecord]:
        """按 story_id 查询事件流（时间/序号正序）。"""
        return self._list(
            """
            SELECT *
            FROM entity_state_events
            WHERE story_id = ?
            ORDER BY committed_at ASC, sequence ASC, event_id ASC
            """,
            (story_id,),
        )

    def list_by_session_id(self, session_id: str) -> List[EntityStateEventRecord]:
        """按 session_id 查询事件流（时间/序号正序）。"""
        return self._list(
            """
            SELECT *
            FROM entity_state_events
            WHERE session_id = ?
            ORDER BY committed_at ASC, sequence ASC, event_id ASC
            """,
            (session_id,),
        )

    def list_by_operation_id(self, operation_id: str) -> List[EntityStateEventRecord]:
        """按 operation_id 查询同批次事件。"""
        return self._list(
            """
            SELECT *
            FROM entity_state_events
            WHERE operation_id = ?
            ORDER BY sequence ASC, committed_at ASC, event_id ASC
            """,
            (operation_id,),
        )

    def delete_by_story_id(self, story_id: str) -> int:
        """删除指定故事的全部事件记录。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entity_state_events WHERE story_id = ?", (story_id,))
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def delete_by_story_id_after_turn(self, story_id: str, source_turn_gt: int) -> int:
        """删除指定故事中 source_turn 大于阈值的事件。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM entity_state_events
                WHERE story_id = ?
                  AND source_turn IS NOT NULL
                  AND source_turn > ?
                """,
                (story_id, int(source_turn_gt)),
            )
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def delete_by_session_id_after_turn(self, session_id: str, source_turn_gt: int) -> int:
        """删除指定会话中 source_turn 大于阈值的事件。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM entity_state_events
                WHERE session_id = ?
                  AND source_turn IS NOT NULL
                  AND source_turn > ?
                """,
                (session_id, int(source_turn_gt)),
            )
            deleted = cursor.rowcount
            conn.commit()
        return int(deleted)

    def _list(self, sql: str, params: tuple[Any, ...]) -> List[EntityStateEventRecord]:
        """执行查询并映射为事件模型列表。"""
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_model(row) for row in rows]

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> EntityStateEventRecord:
        """将数据库行对象转换为 EntityStateEventRecord。"""
        return EntityStateEventRecord(
            event_id=row["event_id"],
            story_id=row["story_id"],
            session_id=row["session_id"],
            entity_id=row["entity_id"],
            entity_type=row["entity_type"],
            entity_name=row["entity_name"],
            field_name=row["field_name"],
            op=row["op"],
            value=_deserialize_payload(row["value_payload"]),
            before=_deserialize_payload(row["before_payload"]),
            after=_deserialize_payload(row["after_payload"]),
            evidence_text=row["evidence_text"],
            source_turn=row["source_turn"],
            source=row["source"],
            operation_id=row["operation_id"],
            sequence=row["sequence"],
            confidence=row["confidence"],
            status=row["status"],
            committed_at=row["committed_at"],
            metadata=_deserialize_payload(row["metadata"]) or {},
        )
