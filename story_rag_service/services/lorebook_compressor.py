"""
Lorebook 条目压缩服务：对超长条目进行 LLM 摘要并缓存。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from prompting import render_prompt

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

COMPRESS_THRESHOLD = 300  # 字符数阈值
COMPRESS_TARGET = 80  # 目标摘要字数


class LorebookCompressor:
    """对长 lorebook 条目做 LLM 摘要，结果缓存在 SQLite。"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化压缩器并确保缓存表存在。"""
        self._db_path = db_path or settings.database_path
        self._local = threading.local()
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地连接，避免跨线程复用 SQLite 连接。"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_table(self):
        """创建缓存表（如不存在）。"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lorebook_summaries (
                entry_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

    def _content_hash(self, content: str) -> str:
        """简单哈希，用于检测内容变化时失效缓存。"""
        import hashlib
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:16]

    def get_cached(self, entry_id: str, content: str) -> Optional[str]:
        """查询缓存，仅在内容未变时返回。"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT summary, content_hash FROM lorebook_summaries WHERE entry_id = ?",
            (entry_id,),
        ).fetchone()
        if row and row["content_hash"] == self._content_hash(content):
            return row["summary"]
        return None

    def save_cache(self, entry_id: str, content: str, summary: str):
        """写入或覆盖指定条目的摘要缓存。"""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO lorebook_summaries
               (entry_id, summary, content_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (entry_id, summary, self._content_hash(content), datetime.utcnow().isoformat()),
        )
        conn.commit()

    async def compress_contexts(
        self,
        contexts: List[Dict[str, Any]],
        llm: Any,
    ) -> List[Dict[str, Any]]:
        """异步压缩 contexts。

        行为约定：
        1. 小于阈值或缺少 entry_id 的条目保持原样；
        2. 优先命中缓存，未命中再调用 LLM；
        3. 压缩后的条目会在 metadata 中标记 `compressed=True`；
        4. 任意异常回退原文，保证链路可用性。
        """
        result = []
        for ctx in contexts:
            content = ctx.get("content", "")
            if len(content) <= COMPRESS_THRESHOLD:
                result.append(ctx)
                continue

            # 兼容两种元数据主键来源：业务 id 与 Chroma 内部 id。
            entry_id = (ctx.get("metadata") or {}).get("id", "") or (ctx.get("metadata") or {}).get("_chroma_id", "")
            if not entry_id:
                result.append(ctx)
                continue

            # 查缓存
            cached = self.get_cached(entry_id, content)
            if cached:
                compressed = {**ctx, "content": cached}
                meta = dict(compressed.get("metadata") or {})
                meta["compressed"] = True
                compressed["metadata"] = meta
                result.append(compressed)
                logger.debug("📦 压缩命中缓存: %s (%d→%d)", ctx.get("name"), len(content), len(cached))
                continue

            # LLM 压缩
            try:
                prompt = render_prompt("lorebook.compress", target=COMPRESS_TARGET, content=content[:1000])
                resp = await llm.ainvoke(prompt)
                summary = resp.content.strip()[:COMPRESS_TARGET * 3]  # 安全截断
                self.save_cache(entry_id, content, summary)
                compressed = {**ctx, "content": summary}
                meta = dict(compressed.get("metadata") or {})
                meta["compressed"] = True
                compressed["metadata"] = meta
                result.append(compressed)
                logger.info("📦 LLM 压缩: %s (%d→%d)", ctx.get("name"), len(content), len(summary))
            except Exception as exc:
                logger.warning("压缩失败，保留原文: %s – %s", ctx.get("name"), exc)
                result.append(ctx)

        return result

    def compress_contexts_sync(
        self,
        contexts: List[Dict[str, Any]],
        llm: Any,
    ) -> List[Dict[str, Any]]:
        """同步版本的条目压缩。

        与 `compress_contexts` 规则一致，仅调用 `llm.invoke` 执行同步推理。
        """
        result = []
        for ctx in contexts:
            content = ctx.get("content", "")
            if len(content) <= COMPRESS_THRESHOLD:
                result.append(ctx)
                continue

            entry_id = (ctx.get("metadata") or {}).get("id", "") or (ctx.get("metadata") or {}).get("_chroma_id", "")
            if not entry_id:
                result.append(ctx)
                continue

            cached = self.get_cached(entry_id, content)
            if cached:
                compressed = {**ctx, "content": cached}
                meta = dict(compressed.get("metadata") or {})
                meta["compressed"] = True
                compressed["metadata"] = meta
                result.append(compressed)
                continue

            try:
                prompt = render_prompt("lorebook.compress", target=COMPRESS_TARGET, content=content[:1000])
                resp = llm.invoke(prompt)
                summary = resp.content.strip()[:COMPRESS_TARGET * 3]
                self.save_cache(entry_id, content, summary)
                compressed = {**ctx, "content": summary}
                meta = dict(compressed.get("metadata") or {})
                meta["compressed"] = True
                compressed["metadata"] = meta
                result.append(compressed)
                logger.info("📦 LLM 压缩(sync): %s (%d→%d)", ctx.get("name"), len(content), len(summary))
            except Exception as exc:
                logger.warning("压缩失败，保留原文: %s – %s", ctx.get("name"), exc)
                result.append(ctx)

        return result
