"""客户端存储 API。

提供通用键值存储能力，让前端将应用状态持久化到后端，
从而在同一服务端下实现多设备共享。

基于现有 SQLite 表，不依赖额外迁移脚本（使用 CREATE TABLE IF NOT EXISTS）。
"""

import sqlite3
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies.auth import get_current_user
from config import settings
from models.user import User

# 模块日志器，用于记录客户端存储接口的异常与诊断信息。
logger = logging.getLogger(__name__)

# 客户端存储路由，统一前缀并归类到 client-storage 标签。
router = APIRouter(prefix="/client-storage", tags=["client-storage"])

# ---------------------------------------------------------------------------
# SQLite 辅助函数
# ---------------------------------------------------------------------------

def _db_path() -> str:
    """返回客户端存储所使用的 SQLite 数据库路径。"""
    return settings.database_path


def _ensure_table(conn: sqlite3.Connection) -> None:
    """确保 client_storage 表存在，首次访问时自动创建。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS client_storage_entries (
            owner_user_id TEXT NOT NULL,
            storage_key  TEXT NOT NULL,
            value        TEXT NOT NULL,
            updated_at   TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (owner_user_id, storage_key)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_client_storage_entries_owner_updated_at
        ON client_storage_entries(owner_user_id, updated_at)
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
    """写入/覆盖存储值时使用的请求体。"""
    value: str


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.get("/{key}", summary="Read a stored value")
def get_value(key: str, current_user: User = Depends(get_current_user)):
    """读取指定 key 对应值；不存在返回 404。"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM client_storage_entries WHERE owner_user_id = ? AND storage_key = ?",
            [current_user.id, key],
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return {"key": key, "value": row["value"]}


@router.put("/{key}", summary="Create or update a stored value")
def set_value(key: str, body: StorageSetRequest, current_user: User = Depends(get_current_user)):
    """创建或更新 key 对应值。"""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO client_storage_entries (owner_user_id, storage_key, value, updated_at)
                 VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(owner_user_id, storage_key)
              DO UPDATE SET value = excluded.value,
                            updated_at = excluded.updated_at
            """,
            [current_user.id, key, body.value],
        )
        conn.commit()
    return {"key": key}


@router.delete("/{key}", summary="Delete a single stored value")
def delete_value(key: str, current_user: User = Depends(get_current_user)):
    """删除指定 key（幂等）。"""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM client_storage_entries WHERE owner_user_id = ? AND storage_key = ?",
            [current_user.id, key],
        )
        conn.commit()
    return {"ok": True}


@router.delete("", summary="Wipe all stored values")
def clear_all(current_user: User = Depends(get_current_user)):
    """清空 client_storage 全部数据（常用于重置设置）。"""
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM client_storage_entries WHERE owner_user_id = ?",
            [current_user.id],
        )
        conn.commit()
    return {"cleared": cur.rowcount}
