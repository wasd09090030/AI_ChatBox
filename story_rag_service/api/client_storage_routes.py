"""客户端存储 API。

提供通用键值存储能力，让前端将应用状态持久化到后端，
从而在同一服务端下实现多设备共享。

基于现有 SQLite 表，不依赖额外迁移脚本（使用 CREATE TABLE IF NOT EXISTS）。
"""

import sqlite3
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter(prefix="/client-storage", tags=["client-storage"])

# ---------------------------------------------------------------------------
# SQLite 辅助函数
# ---------------------------------------------------------------------------

def _db_path() -> str:
    """功能：处理数据库路径。"""
    return settings.database_path


def _ensure_table(conn: sqlite3.Connection) -> None:
    """功能：确保 table。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS client_storage (
            storage_key  TEXT PRIMARY KEY,
            value        TEXT NOT NULL,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _connect() -> sqlite3.Connection:
    """打开连接并确保表结构可用。"""
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class StorageSetRequest(BaseModel):
    """作用：定义 StorageSetRequest 数据结构，用于约束字段语义与序列化格式。"""
    value: str


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.get("/{key}", summary="Read a stored value")
def get_value(key: str):
    """读取指定 key 对应值；不存在返回 404。"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM client_storage WHERE storage_key = ?", [key]
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return {"key": key, "value": row["value"]}


@router.put("/{key}", summary="Create or update a stored value")
def set_value(key: str, body: StorageSetRequest):
    """创建或更新 key 对应值。"""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO client_storage (storage_key, value, updated_at)
                 VALUES (?, ?, datetime('now'))
            ON CONFLICT(storage_key)
              DO UPDATE SET value = excluded.value,
                            updated_at = excluded.updated_at
            """,
            [key, body.value],
        )
        conn.commit()
    return {"key": key}


@router.delete("/{key}", summary="Delete a single stored value")
def delete_value(key: str):
    """删除指定 key（幂等）。"""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM client_storage WHERE storage_key = ?", [key]
        )
        conn.commit()
    return {"ok": True}


@router.delete("", summary="Wipe all stored values")
def clear_all():
    """清空 client_storage 全部数据（常用于重置设置）。"""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM client_storage")
        conn.commit()
    return {"cleared": cur.rowcount}
