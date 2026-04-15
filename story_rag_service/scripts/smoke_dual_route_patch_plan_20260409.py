"""
Smoke validation runner for Plan_2026-04-09 dual-route + structured entity patch.

Coverage (backend-focused):
1) Contract and persistence prerequisites:
   - `entity_state_events` table exists with required columns.
   - generate/stream/regenerate responses expose:
     - entity_state_snapshot
     - entity_state_updates
     - world_update
2) Structured patch behavior:
   - At least one generate round yields field-level entity_state_updates.
   - entity_state_updates payload is structurally valid.
3) Operation chain alignment:
   - memory_update_journal and entity patch updates share operation_id/sequence chain.
4) Replay/rebuild paths:
   - rollback/session-rebuild/story-rebuild can surface replay evidence.
   - story segment rollback and adjustment commit keep entity rebuild behavior visible.
5) Story deletion cleanup:
   - delete story also clears entity_state_events for this story.

Usage:
  python scripts/smoke_dual_route_patch_plan_20260409.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_USER_ID=user_xxx
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
  SMOKE_TIMEOUT=180
  SMOKE_DB_PATH=.../story_rag_service/data/chatbox.db
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

# 服务基础地址（可通过环境变量覆盖）。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# 请求头用户标识。
USER_ID = os.getenv("SMOKE_USER_ID", "user_1773820783085_bk1gzshza")
# 冒烟测试使用的模型提供商。
PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek")
# 冒烟测试使用的模型名称。
MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat")
# HTTP 请求超时时间（秒）。
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT", "180"))

# 默认 SQLite 数据库路径。
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "chatbox.db"
# SQLite 数据库路径（支持环境变量覆盖）。
DB_PATH = Path(os.getenv("SMOKE_DB_PATH", str(DEFAULT_DB_PATH)))

# 报告输出目录。
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "TestResult"
# 报告 JSON 文件路径。
REPORT_JSON = REPORT_DIR / "Plan0409_DualRoutePatch_Validation_Run.json"

# 结构化实体补丁允许更新的字段集合。
PATCH_FIELDS = {
    "current_location",
    "inventory",
    "status_tags",
    "companions",
    "short_goal",
    "state_summary",
}
# 结构化实体补丁允许的操作类型集合。
PATCH_OPS = {"set", "add", "remove", "clear", "reset"}


@dataclass
class Check:
    """记录单个校验项的结果与证据细节。"""
    name: str
    passed: bool
    detail: dict[str, Any]


def _headers() -> dict[str, str]:
    """构造请求头并注入用户标识。"""
    return {"X-User-ID": USER_ID}


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    payload: Optional[dict[str, Any]] = None,
    with_user: bool = False,
) -> tuple[int, dict[str, Any]]:
    """统一封装 HTTP 请求并返回状态码与 JSON 响应。"""
    headers = _headers() if with_user else {}
    try:
        response = client.request(method.upper(), f"{BASE_URL}{path}", json=payload, headers=headers)
    except httpx.RequestError as exc:
        return 0, {
            "error": str(exc),
            "exception_type": type(exc).__name__,
            "path": path,
            "method": method.upper(),
        }
    try:
        body = response.json() if response.text else {}
    except Exception:
        body = {"raw": response.text}
    return response.status_code, body


def _stream_generate(
    client: httpx.Client,
    payload: dict[str, Any],
    *,
    with_user: bool,
) -> tuple[int, dict[str, Any], int]:
    """调用 SSE 生成接口并提取 done 事件与分片计数。"""
    headers = _headers() if with_user else {}
    final_event: dict[str, Any] = {}
    chunk_count = 0

    try:
        with client.stream("POST", f"{BASE_URL}/api/v2/story/generate/stream", json=payload, headers=headers) as response:
            status = response.status_code
            if status != 200:
                return status, {}, 0

            buffer = ""
            for text in response.iter_text():
                if not text:
                    continue
                buffer += text
                lines = buffer.split("\n")
                buffer = lines.pop() if lines else ""

                for line in lines:
                    normalized = line.strip()
                    if not normalized.startswith("data: "):
                        continue
                    try:
                        event = json.loads(normalized[6:])
                    except Exception:
                        continue

                    if event.get("done") is False:
                        chunk_count += 1
                        continue
                    if event.get("done") is True:
                        final_event = event
                        return status, final_event, chunk_count
    except httpx.RequestError as exc:
        return 0, {
            "error": str(exc),
            "exception_type": type(exc).__name__,
            "path": "/api/v2/story/generate/stream",
            "method": "POST",
        }, 0

    return 200, final_event, chunk_count


def _add(checks: list[Check], cond: bool, name: str, detail: dict[str, Any]) -> None:
    """追加一条检查结果。"""
    checks.append(Check(name=name, passed=bool(cond), detail=detail))


def _extract_items_from_snapshot(snapshot: Any) -> list[dict[str, Any]]:
    """从实体快照中提取合法的实体条目列表。"""
    if not isinstance(snapshot, dict):
        return []
    raw_items = snapshot.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _find_entity(items: list[dict[str, Any]], display_name: str) -> Optional[dict[str, Any]]:
    """按展示名在实体列表中查找目标实体。"""
    for item in items:
        if str(item.get("display_name") or "").strip() == display_name:
            return item
    return None


def _has_entity_update(memory_updates: list[dict[str, Any]], *, source: Optional[str] = None) -> bool:
    """判断更新列表中是否存在实体状态层事件。"""
    for item in memory_updates:
        if item.get("memory_layer") != "entity_state":
            continue
        if source is not None and item.get("source") != source:
            continue
        return True
    return False


def _operation_ids(memory_updates: list[dict[str, Any]], memory_layer: str) -> set[str]:
    """提取指定记忆层的 operation_id 集合。"""
    return {
        str(item.get("operation_id"))
        for item in memory_updates
        if item.get("memory_layer") == memory_layer and item.get("operation_id")
    }


def _all_operation_ids(memory_updates: list[dict[str, Any]]) -> set[str]:
    """提取全部更新事件中的 operation_id 集合。"""
    return {str(item.get("operation_id")) for item in memory_updates if item.get("operation_id")}


def _is_positive_int(value: Any) -> bool:
    """判断值是否为正整数。"""
    return isinstance(value, int) and value > 0


def _validate_entity_updates(
    updates: list[dict[str, Any]],
    *,
    expected_source: Optional[str] = None,
) -> tuple[bool, dict[str, Any]]:
    """校验实体更新。"""
    errors: list[str] = []
    sequences: list[int] = []
    operation_ids: set[str] = set()

    for idx, update in enumerate(updates):
        if not isinstance(update, dict):
            errors.append(f"index={idx}: non-dict update")
            continue

        field_name = update.get("field_name")
        op = update.get("op")
        operation_id = update.get("operation_id")
        sequence = update.get("sequence")

        if field_name not in PATCH_FIELDS:
            errors.append(f"index={idx}: invalid field_name={field_name}")
        if op not in PATCH_OPS:
            errors.append(f"index={idx}: invalid op={op}")
        if not str(update.get("entity_id") or "").strip():
            errors.append(f"index={idx}: missing entity_id")
        if expected_source and update.get("source") != expected_source:
            errors.append(
                f"index={idx}: source mismatch expected={expected_source} actual={update.get('source')}"
            )
        if not str(operation_id or "").strip():
            errors.append(f"index={idx}: missing operation_id")
        else:
            operation_ids.add(str(operation_id))
        if not _is_positive_int(sequence):
            errors.append(f"index={idx}: invalid sequence={sequence}")
        else:
            sequences.append(int(sequence))

    sorted_sequences = sorted(sequences)
    monotonic = sequences == sorted_sequences if sequences else True
    if sequences and not monotonic:
        errors.append("sequence list is not monotonic in payload order")

    return (
        len(errors) == 0,
        {
            "count": len(updates),
            "operation_ids": sorted(operation_ids),
            "sequences": sequences,
            "errors": errors[:12],
            "preview": updates[:3],
        },
    )


def _extract_patch_meta(world_update: Any) -> dict[str, Any]:
    """从世界更新对象中提取 entity_patch 元信息。"""
    if not isinstance(world_update, dict):
        return {}
    entity_patch = world_update.get("entity_patch")
    if not isinstance(entity_patch, dict):
        return {}
    return entity_patch


def _timeline_entity_sources(items: list[dict[str, Any]]) -> set[str]:
    """收集时间线里实体状态事件的来源集合。"""
    return {
        str(item.get("source"))
        for item in items
        if item.get("memory_layer") == "entity_state" and item.get("source")
    }


def _db_enabled() -> bool:
    """检查本地 SQLite 文件是否可用。"""
    return DB_PATH.exists()


def _db_fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """执行查询并返回字典列表，失败时返回空列表。"""
    if not _db_enabled():
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return []


def _db_table_exists(table_name: str) -> bool:
    """判断指定数据表是否存在。"""
    rows = _db_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return bool(rows)


def _db_table_columns(table_name: str) -> set[str]:
    """读取指定数据表的列名集合。"""
    rows = _db_fetchall(f"PRAGMA table_info({table_name})")
    return {str(row.get("name")) for row in rows if row.get("name")}


def _db_count_entity_events(
    *,
    story_id: Optional[str] = None,
    session_id: Optional[str] = None,
    operation_id: Optional[str] = None,
) -> int:
    """按过滤条件统计 entity_state_events 表记录数。"""
    clauses: list[str] = []
    params: list[Any] = []
    if story_id:
        clauses.append("story_id = ?")
        params.append(story_id)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if operation_id:
        clauses.append("operation_id = ?")
        params.append(operation_id)

    sql = "SELECT COUNT(1) AS cnt FROM entity_state_events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    rows = _db_fetchall(sql, tuple(params))
    return int(rows[0].get("cnt") or 0) if rows else 0


def _db_list_entity_events(
    *,
    story_id: Optional[str] = None,
    session_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """按过滤条件查询 entity_state_events 表的最近记录。"""
    clauses: list[str] = []
    params: list[Any] = []
    if story_id:
        clauses.append("story_id = ?")
        params.append(story_id)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if operation_id:
        clauses.append("operation_id = ?")
        params.append(operation_id)

    sql = (
        "SELECT event_id, story_id, session_id, entity_id, entity_name, field_name, op, "
        "source, source_turn, operation_id, sequence, status, committed_at "
        "FROM entity_state_events"
    )
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY committed_at DESC, COALESCE(sequence, 0) DESC LIMIT ?"
    params.append(max(1, int(limit)))
    return _db_fetchall(sql, tuple(params))


def _db_count_memory_journal(
    *,
    session_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    memory_layer: Optional[str] = None,
) -> int:
    """按过滤条件统计 memory_update_journal 表记录数。"""
    clauses: list[str] = []
    params: list[Any] = []
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if operation_id:
        clauses.append("operation_id = ?")
        params.append(operation_id)
    if memory_layer:
        clauses.append("memory_layer = ?")
        params.append(memory_layer)

    sql = "SELECT COUNT(1) AS cnt FROM memory_update_journal"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    rows = _db_fetchall(sql, tuple(params))
    return int(rows[0].get("cnt") or 0) if rows else 0


def _preflight(client: httpx.Client, checks: list[Check]) -> None:
    """执行健康检查与模型提供商连通性前置校验。"""
    status, body = _request(client, "GET", "/api/v2/health")
    _add(checks, status == 200 and body.get("status") == "healthy", "health", {"status": status, "body": body})

    status, body = _request(client, "GET", "/api/v2/providers", with_user=True)
    providers = {item.get("provider"): item for item in body.get("providers", [])} if status == 200 else {}
    provider_ready = bool(providers.get(PROVIDER, {}).get("available"))
    _add(
        checks,
        status == 200 and provider_ready,
        "provider_ready",
        {"status": status, "provider": providers.get(PROVIDER)},
    )

    status, body = _request(
        client,
        "POST",
        "/api/v2/providers/test-connection",
        payload={"provider": PROVIDER, "base_url": None},
        with_user=True,
    )
    _add(
        checks,
        status == 200 and body.get("success") is True,
        "provider_connection",
        {"status": status, "body": body},
    )


def run_smoke() -> dict[str, Any]:
    """执行双路径与结构化实体补丁的端到端冒烟验证。"""
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        _preflight(client, checks)

        db_ready = _db_enabled()
        _add(
            checks,
            db_ready,
            "db_path_exists",
            {"db_path": str(DB_PATH), "exists": db_ready},
        )

        table_exists = _db_table_exists("entity_state_events") if db_ready else False
        _add(
            checks,
            table_exists,
            "entity_state_events_table_exists",
            {"db_path": str(DB_PATH), "table_exists": table_exists},
        )

        required_columns = {
            "event_id",
            "story_id",
            "session_id",
            "entity_id",
            "field_name",
            "op",
            "before_payload",
            "after_payload",
            "source",
            "operation_id",
            "sequence",
            "status",
            "committed_at",
        }
        actual_columns = _db_table_columns("entity_state_events") if db_ready and table_exists else set()
        missing_columns = sorted(required_columns - actual_columns)
        _add(
            checks,
            db_ready and table_exists and not missing_columns,
            "entity_state_events_columns_ready",
            {
                "required_columns": sorted(required_columns),
                "actual_columns": sorted(actual_columns),
                "missing_columns": missing_columns,
            },
        )

        suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        world_name = f"Plan0409-双路Patch验证-{suffix}"
        story_title = "双路Patch验证：钟楼与地下仓库"

        status, body = _request(
            client,
            "POST",
            "/api/v2/worlds",
            payload={"name": world_name, "description": "Plan 04-09 双路Patch验证世界", "genre": "mystery"},
        )
        world_id = body.get("id") if isinstance(body, dict) else None
        _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

        status, loc_top = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/location",
            payload={
                "name": "钟楼顶层",
                "description": "可俯瞰旧港的高处平台",
                "region": "旧港",
            },
        )
        location_top_id = loc_top.get("entry_id") if isinstance(loc_top, dict) else None
        _add(
            checks,
            status == 200 and bool(location_top_id),
            "location_create_top",
            {"status": status, "entry_id": location_top_id},
        )

        status, loc_warehouse = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/location",
            payload={
                "name": "地下仓库",
                "description": "潮湿阴冷、堆满旧木箱的空间",
                "region": "旧港",
            },
        )
        location_warehouse_id = loc_warehouse.get("entry_id") if isinstance(loc_warehouse, dict) else None
        _add(
            checks,
            status == 200 and bool(location_warehouse_id),
            "location_create_warehouse",
            {"status": status, "entry_id": location_warehouse_id},
        )

        status, zhangsan_create = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/character",
            payload={
                "name": "张三",
                "personality": "冷静谨慎",
                "background": "调查员",
                "inventory": [],
                "current_location": "钟楼外",
            },
        )
        zhangsan_id = zhangsan_create.get("entry_id") if isinstance(zhangsan_create, dict) else None
        _add(
            checks,
            status == 200 and bool(zhangsan_id),
            "character_create_zhangsan",
            {"status": status, "entry_id": zhangsan_id},
        )

        status, lisi_create = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/character",
            payload={
                "name": "李四",
                "personality": "敏锐急躁",
                "background": "向导",
                "inventory": ["火折子"],
                "current_location": "钟楼外",
            },
        )
        lisi_id = lisi_create.get("entry_id") if isinstance(lisi_create, dict) else None
        _add(checks, status == 200 and bool(lisi_id), "character_create_lisi", {"status": status, "entry_id": lisi_id})

        status, story_body = _request(
            client,
            "POST",
            "/api/v2/stories",
            payload={"world_id": world_id, "title": story_title, "metadata": {"creation_mode": "improv"}},
        )
        story_id = story_body.get("id") if isinstance(story_body, dict) else None
        _add(checks, status == 200 and bool(story_id), "story_create", {"status": status, "story_id": story_id})

        session_id = f"story-{story_id}-v2"
        status, body = _request(
            client,
            "POST",
            "/api/v2/story/session",
            payload={"session_id": session_id, "world_id": world_id},
            with_user=True,
        )
        _add(checks, status == 200 and body.get("session_id") == session_id, "session_create", {"status": status, "body": body})

        if not world_id or not story_id:
            _add(
                checks,
                False,
                "critical_ids_available",
                {"world_id": world_id, "story_id": story_id, "reason": "critical id missing, skip remaining checks"},
            )
            result = {
                "summary": {
                    "total": len(checks),
                    "passed": sum(1 for item in checks if item.passed),
                    "failed": sum(1 for item in checks if not item.passed),
                    "all_passed": False,
                    "base_url": BASE_URL,
                    "provider": PROVIDER,
                    "model": MODEL,
                    "db_path": str(DB_PATH),
                    "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "checks": [item.__dict__ for item in checks],
                "evidence": evidence,
            }
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result

        base_payload = {
            "session_id": session_id,
            "story_id": story_id,
            "world_id": world_id,
            "provider": PROVIDER,
            "model": MODEL,
            "mode": "narrative",
            "temperature": 0.4,
            "max_tokens": 320,
            "creation_mode": "improv",
            "progress_intent": "hold",
        }

        generate_prompts = [
            "请推进剧情并明确写出：张三来到钟楼顶层，张三拿到铜钥匙，李四与张三结伴行动。",
            "本轮必须包含明确状态变化：张三当前位置=钟楼顶层；张三inventory新增铜钥匙；张三companions包含李四。",
            "写一段短剧情，事实要求：张三在钟楼顶层并持有铜钥匙，李四与张三同行。",
        ]

        generate_status = 0
        generate_body: dict[str, Any] = {}
        generate_used_prompt = ""
        generate_attempts: list[dict[str, Any]] = []

        for prompt in generate_prompts:
            status, body = _request(
                client,
                "POST",
                "/api/v2/story/generate",
                payload={**base_payload, "user_input": prompt},
                with_user=True,
            )
            updates = list(body.get("entity_state_updates") or []) if isinstance(body, dict) else []
            patch_meta = _extract_patch_meta(body.get("world_update") if isinstance(body, dict) else None)
            patch_count = patch_meta.get("patch_count") if isinstance(patch_meta, dict) else None

            generate_attempts.append(
                {
                    "status": status,
                    "prompt": prompt,
                    "patch_count": patch_count,
                    "update_count": len(updates),
                    "has_snapshot": isinstance(body.get("entity_state_snapshot"), dict) if isinstance(body, dict) else False,
                }
            )
            generate_status = status
            generate_body = body if isinstance(body, dict) else {}
            generate_used_prompt = prompt
            if status == 200 and isinstance(body, dict) and updates:
                break

        generate_snapshot = generate_body.get("entity_state_snapshot") if isinstance(generate_body, dict) else None
        generate_items = _extract_items_from_snapshot(generate_snapshot)
        generate_updates = list(generate_body.get("entity_state_updates") or []) if isinstance(generate_body, dict) else []
        generate_world_update = generate_body.get("world_update") if isinstance(generate_body, dict) else None
        generate_patch_meta = _extract_patch_meta(generate_world_update)
        generate_patch_count = generate_patch_meta.get("patch_count") if isinstance(generate_patch_meta, dict) else None
        generate_memory_updates = list(generate_body.get("memory_updates") or []) if isinstance(generate_body, dict) else []

        _add(
            checks,
            generate_status == 200
            and isinstance(generate_snapshot, dict)
            and isinstance(generate_updates, list)
            and isinstance(generate_world_update, dict),
            "generate_contract_fields",
            {
                "status": generate_status,
                "used_prompt": generate_used_prompt,
                "attempts": generate_attempts,
                "snapshot_total": len(generate_items),
                "update_count": len(generate_updates),
                "world_update": generate_world_update,
            },
        )

        _add(
            checks,
            generate_status == 200 and len(generate_updates) > 0,
            "generate_patch_updates_present",
            {
                "status": generate_status,
                "used_prompt": generate_used_prompt,
                "attempts": generate_attempts,
                "update_count": len(generate_updates),
            },
        )

        updates_ok, updates_detail = _validate_entity_updates(generate_updates, expected_source="generate")
        _add(
            checks,
            updates_ok and len(generate_updates) > 0,
            "generate_patch_updates_schema_valid",
            updates_detail,
        )

        patch_meta_valid = (
            isinstance(generate_patch_count, int)
            and generate_patch_count >= 0
            and isinstance(generate_patch_meta.get("warnings", []), list)
            and isinstance(generate_patch_meta.get("fallback_used"), bool)
            and generate_patch_count == len(generate_updates)
        )
        _add(
            checks,
            patch_meta_valid,
            "generate_world_update_patch_meta",
            {
                "patch_meta": generate_patch_meta,
                "update_count": len(generate_updates),
            },
        )

        _add(
            checks,
            _has_entity_update(generate_memory_updates, source="generate"),
            "generate_memory_updates_contains_entity_state",
            {"memory_updates": generate_memory_updates[:12], "total": len(generate_memory_updates)},
        )

        generate_episodic_ops = _operation_ids(generate_memory_updates, "episodic")
        generate_entity_ops = _operation_ids(generate_memory_updates, "entity_state")
        generate_shared_ops = sorted(generate_episodic_ops.intersection(generate_entity_ops))
        _add(
            checks,
            bool(generate_shared_ops),
            "generate_operation_chain_aligned",
            {
                "episodic_operation_ids": sorted(generate_episodic_ops),
                "entity_operation_ids": sorted(generate_entity_ops),
                "shared_operation_ids": generate_shared_ops,
            },
        )

        _add(
            checks,
            any(op.startswith("generate:") for op in generate_shared_ops),
            "generate_operation_id_prefix",
            {"shared_operation_ids": generate_shared_ops},
        )

        generate_primary_op = generate_shared_ops[0] if generate_shared_ops else None
        generate_event_count_by_op = _db_count_entity_events(operation_id=generate_primary_op) if generate_primary_op else 0
        _add(
            checks,
            (not generate_primary_op) or (len(generate_updates) == 0) or (generate_event_count_by_op >= len(generate_updates)),
            "generate_entity_events_persisted",
            {
                "operation_id": generate_primary_op,
                "expected_min": len(generate_updates),
                "db_count": generate_event_count_by_op,
                "db_path": str(DB_PATH),
            },
        )

        generate_journal_entity_count = (
            _db_count_memory_journal(
                session_id=session_id,
                operation_id=generate_primary_op,
                memory_layer="entity_state",
            )
            if generate_primary_op
            else 0
        )
        _add(
            checks,
            (not generate_primary_op) or generate_journal_entity_count >= 1,
            "generate_memory_journal_chain_present",
            {
                "operation_id": generate_primary_op,
                "entity_journal_count": generate_journal_entity_count,
            },
        )

        status, session_entity = _request(client, "GET", f"/api/v2/story/session/{session_id}/entity-state")
        session_items = list(session_entity.get("items") or []) if isinstance(session_entity, dict) else []
        _add(
            checks,
            status == 200 and len(session_items) >= 1,
            "session_entity_state_read_after_generate",
            {"status": status, "total": len(session_items)},
        )

        stream_input = "请明确写出：张三转移到地下仓库，并将铜钥匙留在原处（物品栏移除铜钥匙）。"
        stream_status, stream_done, stream_chunks = _stream_generate(
            client,
            {**base_payload, "user_input": stream_input, "temperature": 0.45},
            with_user=True,
        )
        stream_snapshot = stream_done.get("entity_state_snapshot") if isinstance(stream_done, dict) else None
        stream_items = _extract_items_from_snapshot(stream_snapshot)
        stream_updates = list(stream_done.get("entity_state_updates") or []) if isinstance(stream_done, dict) else []
        stream_world_update = stream_done.get("world_update") if isinstance(stream_done, dict) else None
        stream_patch_meta = _extract_patch_meta(stream_world_update)
        stream_memory_updates = list(stream_done.get("memory_updates") or []) if isinstance(stream_done, dict) else []

        _add(
            checks,
            stream_status == 200
            and bool(stream_done.get("done") is True)
            and isinstance(stream_snapshot, dict)
            and isinstance(stream_updates, list)
            and isinstance(stream_world_update, dict),
            "stream_done_contract_fields",
            {
                "status": stream_status,
                "chunk_count": stream_chunks,
                "snapshot_total": len(stream_items),
                "update_count": len(stream_updates),
                "patch_meta": stream_patch_meta,
            },
        )

        stream_updates_ok, stream_updates_detail = _validate_entity_updates(stream_updates, expected_source="generate")
        _add(
            checks,
            (len(stream_updates) == 0) or stream_updates_ok,
            "stream_patch_updates_schema_valid_if_present",
            stream_updates_detail,
        )

        stream_patch_count = stream_patch_meta.get("patch_count") if isinstance(stream_patch_meta, dict) else None
        _add(
            checks,
            isinstance(stream_patch_count, int)
            and stream_patch_count >= 0
            and isinstance(stream_patch_meta.get("warnings", []), list)
            and isinstance(stream_patch_meta.get("fallback_used"), bool)
            and stream_patch_count == len(stream_updates),
            "stream_world_update_patch_meta",
            {
                "patch_meta": stream_patch_meta,
                "update_count": len(stream_updates),
            },
        )

        stream_episodic_ops = _operation_ids(stream_memory_updates, "episodic")
        stream_entity_ops = _operation_ids(stream_memory_updates, "entity_state")
        stream_shared_ops = sorted(stream_episodic_ops.intersection(stream_entity_ops))
        _add(
            checks,
            bool(stream_shared_ops),
            "stream_operation_chain_aligned",
            {
                "episodic_operation_ids": sorted(stream_episodic_ops),
                "entity_operation_ids": sorted(stream_entity_ops),
                "shared_operation_ids": stream_shared_ops,
            },
        )

        stream_primary_op = stream_shared_ops[0] if stream_shared_ops else None
        stream_event_count_by_op = _db_count_entity_events(operation_id=stream_primary_op) if stream_primary_op else 0
        _add(
            checks,
            (not stream_primary_op) or (len(stream_updates) == 0) or (stream_event_count_by_op >= len(stream_updates)),
            "stream_entity_events_persisted_if_patch",
            {
                "operation_id": stream_primary_op,
                "expected_min": len(stream_updates),
                "db_count": stream_event_count_by_op,
            },
        )

        zhangsan_stream = _find_entity(stream_items, "张三")
        stream_location = str((zhangsan_stream or {}).get("current_location") or "")
        stream_inventory = list((zhangsan_stream or {}).get("inventory") or [])
        _add(
            checks,
            isinstance(zhangsan_stream, dict)
            and stream_location == "地下仓库"
            and "铜钥匙" not in stream_inventory,
            "stream_state_transition_visible",
            {
                "zhangsan": zhangsan_stream,
                "stream_done_preview": str(stream_done.get("generated_text") or stream_done.get("output_text") or "")[:180],
            },
        )

        regenerate_payload = {
            "story_id": story_id,
            "provider": PROVIDER,
            "model": MODEL,
            "mode": "narrative",
            "temperature": 0.45,
            "max_tokens": 320,
            "creation_mode": "improv",
            "progress_intent": "hold",
        }
        status, regenerate_body = _request(
            client,
            "POST",
            f"/api/v2/story/session/{session_id}/regenerate",
            payload=regenerate_payload,
            with_user=True,
        )
        regenerate_snapshot = regenerate_body.get("entity_state_snapshot") if isinstance(regenerate_body, dict) else None
        regenerate_updates = list(regenerate_body.get("entity_state_updates") or []) if isinstance(regenerate_body, dict) else []
        regenerate_world_update = regenerate_body.get("world_update") if isinstance(regenerate_body, dict) else None
        regenerate_patch_meta = _extract_patch_meta(regenerate_world_update)
        regenerate_memory_updates = list(regenerate_body.get("memory_updates") or []) if isinstance(regenerate_body, dict) else []

        _add(
            checks,
            status == 200
            and isinstance(regenerate_snapshot, dict)
            and isinstance(regenerate_updates, list)
            and isinstance(regenerate_world_update, dict),
            "regenerate_contract_fields",
            {
                "status": status,
                "snapshot_total": len(_extract_items_from_snapshot(regenerate_snapshot)),
                "update_count": len(regenerate_updates),
                "patch_meta": regenerate_patch_meta,
            },
        )

        regenerate_updates_ok, regenerate_updates_detail = _validate_entity_updates(
            regenerate_updates,
            expected_source="generate",
        )
        _add(
            checks,
            (len(regenerate_updates) == 0) or regenerate_updates_ok,
            "regenerate_patch_updates_schema_valid_if_present",
            regenerate_updates_detail,
        )

        _add(
            checks,
            _has_entity_update(regenerate_memory_updates),
            "regenerate_memory_updates_contains_entity_state",
            {"memory_updates_preview": regenerate_memory_updates[:12], "total": len(regenerate_memory_updates)},
        )

        regenerate_op_ids = sorted(_all_operation_ids(regenerate_memory_updates))
        _add(
            checks,
            len(regenerate_op_ids) == 1 and regenerate_op_ids[0].startswith("regenerate:"),
            "regenerate_operation_chain_single_id",
            {"operation_ids": regenerate_op_ids},
        )

        regenerate_primary_op = regenerate_op_ids[0] if len(regenerate_op_ids) == 1 else None
        regenerate_patch_count = regenerate_patch_meta.get("patch_count") if isinstance(regenerate_patch_meta, dict) else None
        regenerate_event_count_by_op = _db_count_entity_events(operation_id=regenerate_primary_op) if regenerate_primary_op else 0
        _add(
            checks,
            (not regenerate_primary_op)
            or (not isinstance(regenerate_patch_count, int))
            or regenerate_patch_count == 0
            or regenerate_event_count_by_op >= int(regenerate_patch_count),
            "regenerate_entity_events_persisted_if_patch",
            {
                "operation_id": regenerate_primary_op,
                "patch_count": regenerate_patch_count,
                "db_count": regenerate_event_count_by_op,
            },
        )

        pre_rollback_event_count = _db_count_entity_events(story_id=story_id, session_id=session_id)
        status, rollback_body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
        rollback_updates = list(rollback_body.get("memory_updates") or []) if isinstance(rollback_body, dict) else []
        rollback_entity_updates = [
            item for item in rollback_updates if isinstance(item, dict) and item.get("memory_layer") == "entity_state"
        ]
        rollback_reasons = [str(item.get("reason") or "") for item in rollback_entity_updates]
        rollback_op_ids = sorted(_all_operation_ids(rollback_updates))

        _add(
            checks,
            status == 200 and bool(rollback_body.get("deleted")),
            "rollback_delete_last_message",
            {"status": status, "body": rollback_body},
        )
        _add(
            checks,
            _has_entity_update(rollback_updates, source="rollback"),
            "rollback_updates_contains_entity_state",
            {"entity_updates": rollback_entity_updates[:12], "total": len(rollback_entity_updates)},
        )
        _add(
            checks,
            len(rollback_op_ids) == 1 and rollback_op_ids[0].startswith("rollback:"),
            "rollback_operation_chain_single_id",
            {"operation_ids": rollback_op_ids},
        )

        replay_reason_found = any(reason.startswith("event_replay:") for reason in rollback_reasons)
        _add(
            checks,
            (pre_rollback_event_count == 0) or replay_reason_found,
            "rollback_prefers_event_replay_when_events_exist",
            {
                "pre_rollback_event_count": pre_rollback_event_count,
                "replay_reason_found": replay_reason_found,
                "reasons_preview": rollback_reasons[:8],
            },
        )

        status, session_after_rollback = _request(client, "GET", f"/api/v2/story/session/{session_id}/entity-state")
        _add(
            checks,
            status == 200 and isinstance(session_after_rollback.get("total"), int),
            "session_entity_state_read_after_rollback",
            {"status": status, "body": session_after_rollback},
        )

        pre_session_rebuild_event_count = _db_count_entity_events(story_id=story_id, session_id=session_id)
        status, session_rebuild = _request(
            client,
            "POST",
            f"/api/v2/story/session/{session_id}/entity-state/rebuild?story_id={story_id}&world_id={world_id}",
        )
        session_rebuild_updates = list(session_rebuild.get("memory_updates") or []) if isinstance(session_rebuild, dict) else []
        session_rebuild_entity_reasons = [
            str(item.get("reason") or "")
            for item in session_rebuild_updates
            if isinstance(item, dict) and item.get("memory_layer") == "entity_state"
        ]
        session_replay_reason_found = any(reason.startswith("event_replay:") for reason in session_rebuild_entity_reasons)

        _add(
            checks,
            status == 200 and bool(session_rebuild.get("rebuilt")) and int(session_rebuild.get("entity_count") or 0) >= 0,
            "session_entity_rebuild_api_success",
            {"status": status, "body": session_rebuild},
        )
        _add(
            checks,
            _has_entity_update(session_rebuild_updates, source="entity_state_session_rebuild_api"),
            "session_entity_rebuild_api_updates_visible",
            {"updates_preview": session_rebuild_updates[:12], "total": len(session_rebuild_updates)},
        )
        _add(
            checks,
            (pre_session_rebuild_event_count == 0) or session_replay_reason_found,
            "session_entity_rebuild_prefers_replay_when_events_exist",
            {
                "pre_event_count": pre_session_rebuild_event_count,
                "replay_reason_found": session_replay_reason_found,
                "reasons_preview": session_rebuild_entity_reasons[:8],
            },
        )

        segment1_prompt = "张三与李四在钟楼顶层会合，张三拿着铜钥匙。"
        segment1_content = "张三警觉观察四周，李四提醒尽快离开。"
        status_seg1, story_after_seg1 = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/segments",
            payload={
                "prompt": segment1_prompt,
                "content": segment1_content,
                "retrieved_context": [],
            },
        )

        segment2_prompt = "张三与李四进入地下仓库，张三放下铜钥匙。"
        segment2_content = "地下仓库里潮湿阴冷，李四握紧火折子继续侦察。"
        status_seg2, story_after_seg2 = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/segments",
            payload={
                "prompt": segment2_prompt,
                "content": segment2_content,
                "retrieved_context": [],
            },
        )
        _add(
            checks,
            status_seg1 == 200 and status_seg2 == 200,
            "seed_story_segments",
            {
                "status_seg1": status_seg1,
                "status_seg2": status_seg2,
                "segment_count": len(list((story_after_seg2 or {}).get("segments") or [])),
            },
        )

        segments_after_seed = list((story_after_seg2 or {}).get("segments") or []) if isinstance(story_after_seg2, dict) else []
        segment2_id = segments_after_seed[-1].get("id") if segments_after_seed else None
        _add(
            checks,
            bool(segment2_id),
            "seed_segment_id_available",
            {"segment2_id": segment2_id},
        )

        commit_content = "张三与李四在地下仓库搜查，张三决定封锁入口并警惕回头路。"
        status, adjustment_commit = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/adjustments/commit",
            payload={
                "session_id": session_id,
                "updates": [
                    {
                        "segment_id": segment2_id,
                        "content": commit_content,
                    }
                ],
            },
        )
        adjustment_updates = list(adjustment_commit.get("memory_updates") or []) if isinstance(adjustment_commit, dict) else []
        _add(
            checks,
            status == 200 and bool(adjustment_commit.get("rebuild_entity_state_rebuilt")),
            "story_adjustment_commit_rebuild_entity",
            {
                "status": status,
                "rebuild_entity_state_rebuilt": adjustment_commit.get("rebuild_entity_state_rebuilt"),
            },
        )
        _add(
            checks,
            _has_entity_update(adjustment_updates, source="story_adjustment_commit"),
            "story_adjustment_commit_entity_updates_visible",
            {"memory_updates": adjustment_updates[:12], "total": len(adjustment_updates)},
        )

        pre_story_segment_rollback_event_count = _db_count_entity_events(story_id=story_id)
        status, segment_rollback = _request(client, "DELETE", f"/api/v2/stories/{story_id}/segments/last")
        segment_rollback_updates = list(segment_rollback.get("memory_updates") or []) if isinstance(segment_rollback, dict) else []
        segment_rollback_entity_reasons = [
            str(item.get("reason") or "")
            for item in segment_rollback_updates
            if isinstance(item, dict) and item.get("memory_layer") == "entity_state"
        ]
        segment_rollback_replay_reason_found = any(
            reason.startswith("event_replay:") for reason in segment_rollback_entity_reasons
        )

        _add(
            checks,
            status == 200 and bool(segment_rollback.get("rebuild_entity_state_rebuilt")),
            "story_segment_rollback_rebuild_entity",
            {
                "status": status,
                "rebuild_entity_state_rebuilt": segment_rollback.get("rebuild_entity_state_rebuilt"),
            },
        )
        _add(
            checks,
            _has_entity_update(segment_rollback_updates, source="story_segment_rollback"),
            "story_segment_rollback_entity_updates_visible",
            {"memory_updates": segment_rollback_updates[:12], "total": len(segment_rollback_updates)},
        )
        _add(
            checks,
            (pre_story_segment_rollback_event_count == 0) or segment_rollback_replay_reason_found,
            "story_segment_rollback_prefers_replay_when_events_exist",
            {
                "pre_event_count": pre_story_segment_rollback_event_count,
                "replay_reason_found": segment_rollback_replay_reason_found,
                "reasons_preview": segment_rollback_entity_reasons[:8],
            },
        )

        pre_story_rebuild_event_count = _db_count_entity_events(story_id=story_id)
        status, story_rebuild = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/entity-state/rebuild?session_id={session_id}",
        )
        story_rebuild_updates = list(story_rebuild.get("memory_updates") or []) if isinstance(story_rebuild, dict) else []
        story_rebuild_reasons = [
            str(item.get("reason") or "")
            for item in story_rebuild_updates
            if isinstance(item, dict) and item.get("memory_layer") == "entity_state"
        ]
        story_rebuild_replay_reason_found = any(reason.startswith("event_replay:") for reason in story_rebuild_reasons)

        _add(
            checks,
            status == 200 and bool(story_rebuild.get("rebuilt")) and int(story_rebuild.get("entity_count") or 0) >= 0,
            "story_entity_rebuild_api_success",
            {"status": status, "body": story_rebuild},
        )
        _add(
            checks,
            _has_entity_update(story_rebuild_updates, source="entity_state_story_rebuild_api"),
            "story_entity_rebuild_api_updates_visible",
            {"memory_updates": story_rebuild_updates[:12], "total": len(story_rebuild_updates)},
        )
        _add(
            checks,
            (pre_story_rebuild_event_count == 0) or story_rebuild_replay_reason_found,
            "story_entity_rebuild_prefers_replay_when_events_exist",
            {
                "pre_event_count": pre_story_rebuild_event_count,
                "replay_reason_found": story_rebuild_replay_reason_found,
                "reasons_preview": story_rebuild_reasons[:8],
            },
        )

        status, final_timeline = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/memory-updates?page=1&page_size=200",
        )
        final_timeline_items = [item for item in list(final_timeline.get("items") or []) if isinstance(item, dict)]
        entity_sources = _timeline_entity_sources(final_timeline_items)
        required_sources = {
            "generate",
            "regenerate",
            "rollback",
            "story_adjustment_commit",
            "story_segment_rollback",
            "entity_state_session_rebuild_api",
            "entity_state_story_rebuild_api",
        }
        missing_sources = sorted(required_sources - entity_sources)
        _add(
            checks,
            status == 200 and not missing_sources,
            "timeline_contains_required_entity_sources",
            {
                "status": status,
                "entity_sources": sorted(entity_sources),
                "missing_sources": missing_sources,
            },
        )

        status, filtered_memory_updates = _request(
            client,
            "GET",
            f"/api/v2/memory-updates?session_id={session_id}&memory_layer=entity_state&source=generate&page=1&page_size=50",
        )
        filtered_total = int(filtered_memory_updates.get("total") or 0) if isinstance(filtered_memory_updates, dict) else 0
        _add(
            checks,
            status == 200 and filtered_total >= 1,
            "memory_updates_filter_entity_state_generate",
            {"status": status, "total": filtered_total},
        )

        pre_delete_story_event_count = _db_count_entity_events(story_id=story_id)
        status, delete_story_body = _request(client, "DELETE", f"/api/v2/stories/{story_id}")
        post_delete_story_event_count = _db_count_entity_events(story_id=story_id)
        _add(
            checks,
            status == 200 and bool(delete_story_body.get("success")),
            "story_delete_success",
            {"status": status, "body": delete_story_body},
        )
        _add(
            checks,
            pre_delete_story_event_count >= 0 and post_delete_story_event_count == 0,
            "story_delete_cleans_entity_state_events",
            {
                "story_id": story_id,
                "pre_delete_event_count": pre_delete_story_event_count,
                "post_delete_event_count": post_delete_story_event_count,
            },
        )

        evidence = {
            "world_id": world_id,
            "story_id": story_id,
            "session_id": session_id,
            "lorebook_entry_ids": {
                "location_top": location_top_id,
                "location_warehouse": location_warehouse_id,
                "zhangsan": zhangsan_id,
                "lisi": lisi_id,
            },
            "db_path": str(DB_PATH),
            "generate": {
                "used_prompt": generate_used_prompt,
                "attempts": generate_attempts,
                "entity_state_snapshot": generate_snapshot,
                "entity_state_updates_preview": generate_updates[:8],
                "world_update": generate_world_update,
                "shared_operation_ids": generate_shared_ops,
                "db_events_preview": _db_list_entity_events(operation_id=generate_primary_op, limit=8)
                if generate_primary_op
                else [],
            },
            "stream": {
                "entity_state_snapshot": stream_snapshot,
                "entity_state_updates_preview": stream_updates[:8],
                "world_update": stream_world_update,
                "shared_operation_ids": stream_shared_ops,
            },
            "regenerate": {
                "entity_state_snapshot": regenerate_snapshot,
                "entity_state_updates_preview": regenerate_updates[:8],
                "world_update": regenerate_world_update,
                "operation_ids": regenerate_op_ids,
            },
            "final_timeline_entity_sources": sorted(entity_sources),
            "timeline_preview": final_timeline_items[:20],
        }

    total = len(checks)
    passed = sum(1 for item in checks if item.passed)
    result = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "all_passed": passed == total,
            "base_url": BASE_URL,
            "provider": PROVIDER,
            "model": MODEL,
            "db_path": str(DB_PATH),
            "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "checks": [item.__dict__ for item in checks],
        "evidence": evidence,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    """运行验证流程并输出结构化结果与报告路径。"""
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nReport written: {REPORT_JSON}")


if __name__ == "__main__":
    main()

