"""
Smoke validation runner for Plan_2026-04-10 story memory merge.

Coverage:
1) Contract-level merge validation:
   - generate response contains story_memory with operation/semantic/runtime/entity/timeline views.
   - stream done event contains story_memory with the same merged views.
   - regenerate response keeps story_memory and compatibility fields.
2) Operation derivation validation:
   - story_memory.operation.operation_id can be derived from current-round memory events.
3) Unified read model validation:
   - GET /api/v2/story/session/{session_id}/story-memory works and returns merged payload.
   - pagination contract works (page_size constraints and page slicing behavior).
4) Compatibility bridge validation:
   - compatibility fields still exist in generate/stream/regenerate payloads.
   - compatibility bridge API /story/session/{session_id}/entity-state stays readable.

Usage:
  python scripts/smoke_story_memory_plan_20260410.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_USER_ID=user_xxx
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
  SMOKE_TIMEOUT=180
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

# 统一服务地址，允许通过环境变量切换到远端或本地实例。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# 为请求统一附带用户头，确保命中用户级配置读取路径。
USER_ID = os.getenv("SMOKE_USER_ID", "user_1773820783085_bk1gzshza")
# 指定冒烟运行使用的模型提供商。
PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek")
# 指定冒烟运行使用的模型名称。
MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat")
# 为 HTTP 请求设置统一超时时间，避免脚本无限阻塞。
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT", "180"))

# 报告输出目录，用于沉淀本次验证结果。
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "TestResult"
# 本次冒烟结果的 JSON 报告路径。
REPORT_JSON = REPORT_DIR / "Plan0410_StoryMemoryMerge_Validation_Run.json"

# Story memory 聚合视图的必备键集合。
STORY_MEMORY_VIEWS = {"operation", "semantic", "runtime", "entity", "timeline"}
# 历史兼容字段集合，用于校验桥接字段未丢失。
COMPAT_FIELDS = {
    "summary_memory_snapshot",
    "runtime_state_snapshot",
    "entity_state_snapshot",
    "entity_state_updates",
    "world_update",
}


@dataclass
class Check:
    """单项检查结果，包含名称、是否通过与证据细节。"""
    name: str
    passed: bool
    detail: dict[str, Any]


def _headers() -> dict[str, str]:
    """构造统一请求头。"""
    return {"X-User-ID": USER_ID}


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    with_user: bool = False,
) -> tuple[int, dict[str, Any]]:
    """统一封装 HTTP 请求并容错解析 JSON 响应体。"""
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
    """执行 SSE 生成请求并提取 done 事件与分片计数。"""
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
    """追加单项检查结果。"""
    checks.append(Check(name=name, passed=bool(cond), detail=detail))


def _operation_ids(events: Any) -> set[str]:
    """从事件列表中提取 operation_id 集合。"""
    if not isinstance(events, list):
        return set()
    ids: set[str] = set()
    for item in events:
        if isinstance(item, dict) and item.get("operation_id"):
            ids.add(str(item.get("operation_id")))
    return ids


def _story_memory_contract(payload: Any) -> dict[str, Any]:
    """校验 story_memory 聚合结构及必备视图是否齐全。"""
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "missing_top": ["story_memory"],
            "missing_views": sorted(STORY_MEMORY_VIEWS),
            "story_memory": None,
        }

    story_memory = payload.get("story_memory")
    if not isinstance(story_memory, dict):
        return {
            "ok": False,
            "missing_top": ["story_memory"],
            "missing_views": sorted(STORY_MEMORY_VIEWS),
            "story_memory": story_memory,
        }

    missing_views = sorted(STORY_MEMORY_VIEWS - set(story_memory.keys()))
    return {
        "ok": not missing_views,
        "missing_top": [],
        "missing_views": missing_views,
        "story_memory": story_memory,
    }


def _compat_fields_contract(payload: Any) -> dict[str, Any]:
    """校验兼容字段是否完整保留。"""
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "missing_fields": sorted(COMPAT_FIELDS),
            "present_fields": [],
        }

    keys = set(payload.keys())
    missing = sorted(COMPAT_FIELDS - keys)
    present = sorted(COMPAT_FIELDS.intersection(keys))
    return {
        "ok": not missing,
        "missing_fields": missing,
        "present_fields": present,
    }


def _operation_derivable(story_memory: Any, event_list: Any) -> dict[str, Any]:
    """验证 story_memory.operation.operation_id 是否可由事件反推。"""
    operation_id = None
    if isinstance(story_memory, dict):
        operation = story_memory.get("operation")
        if isinstance(operation, dict) and operation.get("operation_id"):
            operation_id = str(operation.get("operation_id"))

    event_op_ids = sorted(_operation_ids(event_list))
    return {
        "ok": bool(operation_id) and operation_id in set(event_op_ids),
        "operation_id": operation_id,
        "event_operation_ids": event_op_ids,
    }


def _preflight(client: httpx.Client, checks: list[Check]) -> None:
    """执行健康检查、Provider 可用性与连通性前置验证。"""
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
    """执行 story_memory 合并与兼容桥接全链路冒烟。"""
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        _preflight(client, checks)

        suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        world_name = f"Plan0410-StoryMemoryMerge-{suffix}"
        story_title = "Story Memory Merge Validation"

        status, world_body = _request(
            client,
            "POST",
            "/api/v2/worlds",
            payload={"name": world_name, "description": "Plan 04-10 Story Memory merge validation", "genre": "mystery"},
        )
        world_id = world_body.get("id") if isinstance(world_body, dict) else None
        _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

        status, zhangsan_create = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/character",
            payload={
                "name": "张三",
                "personality": "冷静",
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

        status, story_body = _request(
            client,
            "POST",
            "/api/v2/stories",
            payload={"world_id": world_id, "title": story_title, "metadata": {"creation_mode": "improv"}},
        )
        story_id = story_body.get("id") if isinstance(story_body, dict) else None
        _add(checks, status == 200 and bool(story_id), "story_create", {"status": status, "story_id": story_id})

        session_id = f"story-{story_id}-v2"
        status, session_body = _request(
            client,
            "POST",
            "/api/v2/story/session",
            payload={"session_id": session_id, "world_id": world_id},
            with_user=True,
        )
        _add(
            checks,
            status == 200 and session_body.get("session_id") == session_id,
            "session_create",
            {"status": status, "body": session_body},
        )

        if not world_id or not story_id:
            _add(
                checks,
                False,
                "critical_ids_available",
                {
                    "world_id": world_id,
                    "story_id": story_id,
                    "reason": "critical id missing, skip remaining checks",
                },
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

        generate_input = "请推进剧情并明确状态变化：张三来到钟楼顶层并获得铜钥匙。"
        generate_status, generate_body = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={**base_payload, "user_input": generate_input},
            with_user=True,
        )

        generate_story_memory_contract = _story_memory_contract(generate_body)
        generate_compat_contract = _compat_fields_contract(generate_body)
        generate_story_memory = generate_story_memory_contract.get("story_memory")
        generate_memory_updates = list(generate_body.get("memory_updates") or []) if isinstance(generate_body, dict) else []
        generate_op_derive = _operation_derivable(generate_story_memory, generate_memory_updates)

        _add(
            checks,
            generate_status == 200 and bool(generate_story_memory_contract.get("ok")),
            "generate_returns_story_memory",
            {
                "status": generate_status,
                "missing_views": generate_story_memory_contract.get("missing_views"),
                "operation": (generate_story_memory or {}).get("operation") if isinstance(generate_story_memory, dict) else None,
            },
        )
        _add(
            checks,
            generate_status == 200 and bool(generate_compat_contract.get("ok")),
            "generate_compat_fields_preserved",
            generate_compat_contract,
        )
        _add(
            checks,
            generate_status == 200 and bool(generate_op_derive.get("ok")),
            "generate_story_memory_operation_derivable",
            generate_op_derive,
        )

        stream_input = "继续推进：张三进入地下仓库并将铜钥匙放入木箱。"
        stream_status, stream_done, stream_chunks = _stream_generate(
            client,
            {**base_payload, "user_input": stream_input, "temperature": 0.45},
            with_user=True,
        )
        stream_story_memory_contract = _story_memory_contract(stream_done)
        stream_compat_contract = _compat_fields_contract(stream_done)
        stream_story_memory = stream_story_memory_contract.get("story_memory")
        stream_memory_updates = list(stream_done.get("memory_updates") or []) if isinstance(stream_done, dict) else []
        stream_op_derive = _operation_derivable(stream_story_memory, stream_memory_updates)

        _add(
            checks,
            stream_status == 200 and stream_done.get("done") is True and bool(stream_story_memory_contract.get("ok")),
            "stream_done_returns_story_memory",
            {
                "status": stream_status,
                "chunk_count": stream_chunks,
                "missing_views": stream_story_memory_contract.get("missing_views"),
                "operation": (stream_story_memory or {}).get("operation") if isinstance(stream_story_memory, dict) else None,
            },
        )
        _add(
            checks,
            stream_status == 200 and bool(stream_compat_contract.get("ok")),
            "stream_done_compat_fields_preserved",
            stream_compat_contract,
        )
        _add(
            checks,
            stream_status == 200 and bool(stream_op_derive.get("ok")),
            "stream_story_memory_operation_derivable",
            stream_op_derive,
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
        regenerate_status, regenerate_body = _request(
            client,
            "POST",
            f"/api/v2/story/session/{session_id}/regenerate",
            payload=regenerate_payload,
            with_user=True,
        )
        regenerate_story_memory_contract = _story_memory_contract(regenerate_body)
        regenerate_compat_contract = _compat_fields_contract(regenerate_body)
        regenerate_story_memory = regenerate_story_memory_contract.get("story_memory")
        regenerate_memory_updates = list(regenerate_body.get("memory_updates") or []) if isinstance(regenerate_body, dict) else []
        regenerate_op_derive = _operation_derivable(regenerate_story_memory, regenerate_memory_updates)

        _add(
            checks,
            regenerate_status == 200 and bool(regenerate_story_memory_contract.get("ok")),
            "regenerate_returns_story_memory",
            {
                "status": regenerate_status,
                "missing_views": regenerate_story_memory_contract.get("missing_views"),
                "operation": (regenerate_story_memory or {}).get("operation") if isinstance(regenerate_story_memory, dict) else None,
            },
        )
        _add(
            checks,
            regenerate_status == 200 and bool(regenerate_compat_contract.get("ok")),
            "regenerate_compat_fields_preserved",
            regenerate_compat_contract,
        )
        _add(
            checks,
            regenerate_status == 200 and bool(regenerate_op_derive.get("ok")),
            "regenerate_story_memory_operation_derivable",
            regenerate_op_derive,
        )

        status, timeline_body = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/memory-updates?page=1&page_size=50",
        )
        timeline_items = [item for item in list(timeline_body.get("items") or []) if isinstance(item, dict)]
        timeline_op_ids = sorted(_operation_ids(timeline_items))
        _add(
            checks,
            status == 200 and len(timeline_items) >= 1,
            "memory_updates_timeline_available",
            {
                "status": status,
                "timeline_total": timeline_body.get("total"),
                "item_count": len(timeline_items),
                "operation_ids": timeline_op_ids,
            },
        )

        status, story_memory_body = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/story-memory?page=1&page_size=50",
        )
        snapshot_story_memory = story_memory_body.get("story_memory") if isinstance(story_memory_body, dict) else None
        snapshot_contract = _story_memory_contract(story_memory_body)
        snapshot_timeline_events = (
            ((snapshot_story_memory or {}).get("timeline") or {}).get("memory_updates")
            if isinstance(snapshot_story_memory, dict)
            else []
        )
        snapshot_operation = (
            ((snapshot_story_memory or {}).get("operation") or {})
            if isinstance(snapshot_story_memory, dict)
            else {}
        )
        snapshot_operation_id = snapshot_operation.get("operation_id") if isinstance(snapshot_operation, dict) else None
        snapshot_event_op_ids = sorted(_operation_ids(snapshot_timeline_events))
        snapshot_entity_updates = (
            ((snapshot_story_memory or {}).get("entity") or {}).get("entity_state_updates")
            if isinstance(snapshot_story_memory, dict)
            else []
        )
        snapshot_entity_op_ids = sorted(_operation_ids(snapshot_entity_updates))
        snapshot_operation_derivable = bool(snapshot_operation_id) and (
            str(snapshot_operation_id) in set(snapshot_event_op_ids)
            or str(snapshot_operation_id) in set(snapshot_entity_op_ids)
        )

        _add(
            checks,
            status == 200 and bool(snapshot_contract.get("ok")),
            "session_story_memory_snapshot_available",
            {
                "status": status,
                "timeline_total": story_memory_body.get("timeline_total") if isinstance(story_memory_body, dict) else None,
                "timeline_page_size": story_memory_body.get("timeline_page_size") if isinstance(story_memory_body, dict) else None,
                "missing_views": snapshot_contract.get("missing_views"),
            },
        )
        _add(
            checks,
            status == 200
            and isinstance(story_memory_body.get("timeline_total"), int)
            and int(story_memory_body.get("timeline_total") or 0) >= len(snapshot_timeline_events),
            "session_story_memory_timeline_shape_valid",
            {
                "timeline_total": story_memory_body.get("timeline_total"),
                "timeline_event_count": len(snapshot_timeline_events),
                "timeline_page": story_memory_body.get("timeline_page"),
                "timeline_page_size": story_memory_body.get("timeline_page_size"),
            },
        )
        _add(
            checks,
            status == 200 and snapshot_operation_derivable,
            "session_story_memory_operation_derivable",
            {
                "operation_id": snapshot_operation_id,
                "timeline_operation_ids": snapshot_event_op_ids,
                "entity_operation_ids": snapshot_entity_op_ids,
            },
        )

        status, story_memory_page_1 = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/story-memory?page=1&page_size=1",
        )
        page_1_updates = (
            (((story_memory_page_1.get("story_memory") or {}).get("timeline") or {}).get("memory_updates") or [])
            if isinstance(story_memory_page_1, dict)
            else []
        )
        _add(
            checks,
            status == 200
            and int(story_memory_page_1.get("timeline_page_size") or 0) == 1
            and len(page_1_updates) <= 1,
            "story_memory_pagination_page_size_effective",
            {
                "status": status,
                "timeline_page_size": story_memory_page_1.get("timeline_page_size") if isinstance(story_memory_page_1, dict) else None,
                "timeline_event_count": len(page_1_updates),
            },
        )

        status, oversize_body = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/story-memory?page=1&page_size=201",
        )
        _add(
            checks,
            status == 422,
            "story_memory_pagination_limit_enforced",
            {
                "status": status,
                "body": oversize_body,
            },
        )

        ghost_session = f"story-memory-ghost-{uuid.uuid4().hex[:8]}"
        status, ghost_body = _request(
            client,
            "GET",
            f"/api/v2/story/session/{ghost_session}/story-memory?page=1&page_size=50",
        )
        _add(
            checks,
            status == 404,
            "story_memory_snapshot_404_for_unknown_session",
            {"status": status, "body": ghost_body, "session_id": ghost_session},
        )

        status, entity_state_body = _request(client, "GET", f"/api/v2/story/session/{session_id}/entity-state")
        _add(
            checks,
            status == 200 and isinstance(entity_state_body.get("items"), list),
            "entity_state_bridge_api_readable",
            {
                "status": status,
                "total": entity_state_body.get("total"),
                "preview": list(entity_state_body.get("items") or [])[:5],
            },
        )

        status, delete_story_body = _request(client, "DELETE", f"/api/v2/stories/{story_id}")
        _add(
            checks,
            status == 200 and bool(delete_story_body.get("success")),
            "story_delete_success",
            {"status": status, "body": delete_story_body},
        )

        evidence = {
            "world_id": world_id,
            "story_id": story_id,
            "session_id": session_id,
            "character_ids": {"zhangsan": zhangsan_id},
            "generate": {
                "status": generate_status,
                "story_memory_operation": ((generate_story_memory or {}).get("operation") if isinstance(generate_story_memory, dict) else None),
                "memory_update_operation_ids": sorted(_operation_ids(generate_memory_updates)),
                "story_memory_preview": generate_story_memory,
            },
            "stream_done": {
                "status": stream_status,
                "chunk_count": stream_chunks,
                "story_memory_operation": ((stream_story_memory or {}).get("operation") if isinstance(stream_story_memory, dict) else None),
                "memory_update_operation_ids": sorted(_operation_ids(stream_memory_updates)),
                "story_memory_preview": stream_story_memory,
            },
            "regenerate": {
                "status": regenerate_status,
                "story_memory_operation": ((regenerate_story_memory or {}).get("operation") if isinstance(regenerate_story_memory, dict) else None),
                "memory_update_operation_ids": sorted(_operation_ids(regenerate_memory_updates)),
                "story_memory_preview": regenerate_story_memory,
            },
            "session_story_memory_snapshot": {
                "response": story_memory_body,
                "timeline_operation_ids": snapshot_event_op_ids,
                "entity_operation_ids": snapshot_entity_op_ids,
            },
            "timeline_preview": timeline_items[:20],
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
            "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "checks": [item.__dict__ for item in checks],
        "evidence": evidence,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    """运行冒烟验证并打印结构化结果与报告路径。"""
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nReport written: {REPORT_JSON}")


if __name__ == "__main__":
    main()
