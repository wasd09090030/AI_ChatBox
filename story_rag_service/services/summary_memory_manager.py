"""
Summary memory manager for long conversation stability.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from prompting import render_prompt


class SummaryMemoryManager:
    """会话摘要记忆管理器。

    负责摘要的读取、增量合并、更新频率判断和可选 LLM 生成。
    """

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库路径、更新间隔与摘要长度上限。"""
        self.db_path = db_path or settings.database_path
        self.update_turn_interval = max(1, settings.summary_update_turn_interval)
        self.max_summary_chars = max(200, settings.summary_max_chars)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        """创建 SQLite 连接并启用按列名访问。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """初始化摘要表，并做向后兼容列补齐。"""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    session_id TEXT PRIMARY KEY,
                    world_id TEXT,
                    summary_text TEXT NOT NULL,
                    key_facts TEXT DEFAULT '[]',
                    entities TEXT DEFAULT '{}',
                    last_turn INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # 阶段 P1-B：兼容已有数据库，增加 entities 列
            try:
                conn.execute("ALTER TABLE conversation_summaries ADD COLUMN entities TEXT DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass  # 列已存在
            conn.commit()

    @staticmethod
    def _parse_json(value: Optional[str], fallback: Any) -> Any:
        """安全解析 JSON 字符串，失败时返回 fallback。"""
        if value is None:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback

    @staticmethod
    def _normalize_facts(facts: Optional[List[str]]) -> List[str]:
        """规范化事实列表：去空白、去重、保持原顺序。"""
        if not facts:
            return []
        normalized = [str(item).strip() for item in facts if str(item).strip()]
        return list(dict.fromkeys(normalized))

    def get_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """读取会话摘要快照，不存在则返回 None。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if not row:
            return None

        return {
            "session_id": row["session_id"],
            "world_id": row["world_id"],
            "summary_text": row["summary_text"],
            "key_facts": self._parse_json(row["key_facts"], []),
            "entities": self._parse_json(row["entities"] if "entities" in row.keys() else None, {}),
            "last_turn": int(row["last_turn"] or 0),
            "updated_at": row["updated_at"],
        }

    def delete_summary(self, session_id: str) -> bool:
        """删除指定会话摘要，返回是否实际删除。"""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM conversation_summaries WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def should_update(self, session_id: str, current_turn: int) -> bool:
        """根据回合间隔判断是否需要触发摘要更新。"""
        summary = self.get_summary(session_id)
        if summary is None:
            return current_turn >= self.update_turn_interval
        return (current_turn - int(summary.get("last_turn", 0))) >= self.update_turn_interval

    def upsert_summary(
        self,
        session_id: str,
        world_id: Optional[str],
        new_summary_text: str,
        new_key_facts: Optional[List[str]],
        last_turn: int,
        entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """写入或更新摘要。

        合并策略：
        1. key_facts 与旧值去重合并并截断；
        2. summary_text 与旧摘要按容量拼接；
        3. entities 进行按键增量合并并做窗口裁剪。
        """
        existing = self.get_summary(session_id)

        merged_facts = self._normalize_facts(new_key_facts)
        merged_summary = (new_summary_text or "").strip()

        # 阶段 P1-B：合并实体信息
        merged_entities: Dict[str, Any] = {}
        if existing and existing.get("entities"):
            merged_entities = dict(existing["entities"])
        if entities:
            for key, values in entities.items():
                if not isinstance(values, list):
                    continue
                old = merged_entities.get(key, [])
                merged_entities[key] = list(dict.fromkeys(old + values))[-12:]

        if existing:
            existing_facts = self._normalize_facts(existing.get("key_facts", []))
            merged_facts = list(dict.fromkeys(existing_facts + merged_facts))[-24:]

            existing_summary_text = (existing.get("summary_text") or "").strip()
            if existing_summary_text and merged_summary:
                candidate = existing_summary_text + "\n" + merged_summary
                if len(candidate) <= self.max_summary_chars:
                    merged_summary = candidate
                else:
                    merged_summary = merged_summary[-self.max_summary_chars:]
            elif existing_summary_text and not merged_summary:
                merged_summary = existing_summary_text[-self.max_summary_chars:]

        if not merged_summary:
            merged_summary = "会话已建立，但尚无可提炼摘要。"

        merged_summary = merged_summary[-self.max_summary_chars:]
        now = datetime.now().isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_summaries (session_id, world_id, summary_text, key_facts, entities, last_turn, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    world_id = excluded.world_id,
                    summary_text = excluded.summary_text,
                    key_facts = excluded.key_facts,
                    entities = excluded.entities,
                    last_turn = excluded.last_turn,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    world_id,
                    merged_summary,
                    json.dumps(merged_facts, ensure_ascii=False),
                    json.dumps(merged_entities, ensure_ascii=False),
                    int(last_turn),
                    now,
                ),
            )
            conn.commit()

        return {
            "session_id": session_id,
            "world_id": world_id,
            "summary_text": merged_summary,
            "key_facts": merged_facts,
            "entities": merged_entities,
            "last_turn": int(last_turn),
            "updated_at": now,
        }

    async def generate_llm_summary(
        self,
        messages_snapshot: List[Dict[str, Any]],
        session_id: str,
        world_id: Optional[str],
        last_turn: int,
        llm: Any,
    ) -> Optional[Dict[str, Any]]:
        """基于最近消息调用 LLM 生成摘要并写库。

        若模型输出不符合 JSON 结构或调用异常，则返回 None 交由上层兜底。
        """
        from langchain_core.messages import HumanMessage, SystemMessage as LCSystemMessage

        if not messages_snapshot:
            return None

        conversation_text = "\n".join(
            f"[{'玩家' if m.get('role') == 'user' else 'AI'}] {m.get('content', '')[:300]}"
            for m in messages_snapshot[-12:]
        )

        prompt_text = render_prompt(
            "summary.user_memory_json",
            conversation_text=conversation_text,
        )

        try:
            result = await asyncio.wait_for(
                llm.ainvoke([
                    LCSystemMessage(content=render_prompt("summary.editor_system")),
                    HumanMessage(content=prompt_text),
                ]),
                timeout=20.0,
            )
            raw_text = (result.content or "").strip()
            if not raw_text:
                raise ValueError("Empty LLM summary")

            # 尝试解析 JSON 格式（LLM 可能包裹 markdown 代码块）
            json_text = raw_text
            if "```" in json_text:
                lines = json_text.split("\n")
                json_lines = [l for l in lines if not l.strip().startswith("```")]
                json_text = "\n".join(json_lines)

            parsed_entities: Dict[str, Any] = {}
            summary_text = raw_text
            try:
                parsed = json.loads(json_text)
                summary_text = parsed.get("summary", raw_text)
                parsed_entities = parsed.get("entities", {})
            except (json.JSONDecodeError, TypeError):
                # 兜底：按旧方式提取
                summary_text = raw_text

            sentences = [s.strip() for s in summary_text.replace("。", "。\n").splitlines() if s.strip()]
            key_facts = sentences[:6]

            return self.upsert_summary(
                session_id=session_id,
                world_id=world_id,
                new_summary_text=summary_text,
                new_key_facts=key_facts,
                last_turn=last_turn,
                entities=parsed_entities,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"LLM summary failed ({exc}), falling back to truncation")
            return None
