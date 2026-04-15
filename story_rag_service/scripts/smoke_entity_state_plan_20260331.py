"""
Smoke validation runner for Plan_2026-03-31 entity-state tracking.

Coverage:
1) Normal generate response includes entity_state_snapshot and entity_state memory updates.
2) Streaming done payload includes entity_state_snapshot.
3) Rollback/regenerate trigger entity-state rebuild visibility.
4) Story adjustment commit and story segment rollback rebuild entity-state.
5) Story/session entity-state rebuild APIs are functional.
6) Session memory timeline includes entity_state events for key sources.

Usage:
  python scripts/smoke_entity_state_plan_20260331.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_USER_ID=user_xxx
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
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
TIMEOUT = 180.0
# 报告输出目录，用于沉淀本次验证结果。
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "TestResult"
# 本次冒烟结果的 JSON 报告路径。
REPORT_JSON = REPORT_DIR / "Plan0331_EntityState_Validation_Run.json"


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
    with_user: bool = False,
) -> tuple[int, dict[str, Any]]:
    """统一封装 HTTP 请求并容错解析 JSON 响应体。"""
    headers = _headers() if with_user else {}
    response = client.request(method.upper(), f"{BASE_URL}{path}", json=payload, headers=headers)
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

    return 200, final_event, chunk_count


def _add(checks: list[Check], cond: bool, name: str, detail: dict[str, Any]) -> None:
    """追加单项检查结果。"""
    checks.append(Check(name=name, passed=bool(cond), detail=detail))


def _find_entity(items: list[dict[str, Any]], display_name: str) -> Optional[dict[str, Any]]:
    """按展示名在实体列表中查找目标实体。"""
    for item in items:
        if str(item.get("display_name") or "").strip() == display_name:
            return item
    return None


def _extract_items_from_snapshot(snapshot: Any) -> list[dict[str, Any]]:
    """从实体快照中提取合法的 items 列表。"""
    if not isinstance(snapshot, dict):
        return []
    raw_items = snapshot.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _has_entity_update(
    memory_updates: list[dict[str, Any]],
    *,
    source: Optional[str] = None,
) -> bool:
    """检查 memory_updates 中是否包含指定来源的 entity_state 事件。"""
    for item in memory_updates:
        if item.get("memory_layer") != "entity_state":
            continue
        if source is not None and item.get("source") != source:
            continue
        return True
    return False


def _operation_ids(memory_updates: list[dict[str, Any]], memory_layer: str) -> set[str]:
    """提取指定 memory_layer 的 operation_id 集合。"""
    return {
        str(item.get("operation_id"))
        for item in memory_updates
        if item.get("memory_layer") == memory_layer and item.get("operation_id")
    }


def _timeline_entity_sources(items: list[dict[str, Any]]) -> set[str]:
    """收集时间线中 entity_state 事件来源集合。"""
    return {
        str(item.get("source"))
        for item in items
        if item.get("memory_layer") == "entity_state" and item.get("source")
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
    _add(checks, status == 200 and body.get("success") is True, "provider_connection", {"status": status, "body": body})


def run_smoke() -> dict[str, Any]:
    """执行实体状态全链路冒烟并输出证据报告。"""
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        _preflight(client, checks)

        suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        world_name = f"Plan0331-实体状态验证-{suffix}"
        story_title = "钟楼与地下仓库：实体状态验证"

        status, body = _request(
            client,
            "POST",
            "/api/v2/worlds",
            payload={"name": world_name, "description": "Plan 03-31 实体状态验证世界", "genre": "mystery"},
        )
        world_id = body.get("id") if isinstance(body, dict) else None
        _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

        status, loc_top = _request(
            client,
            "POST",
            f"/api/v2/worlds/{world_id}/lorebook/location",
            payload={
                "name": "钟楼顶层",
                "description": "高处能俯瞰港口的钟楼平台",
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
                "description": "潮湿阴冷、堆满旧木箱的地下空间",
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
                "inventory": ["绷带"],
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
                "personality": "急躁敏锐",
                "background": "向导",
                "inventory": [],
                "current_location": "钟楼外",
            },
        )
        lisi_id = lisi_create.get("entry_id") if isinstance(lisi_create, dict) else None
        _add(checks, status == 200 and bool(lisi_id), "character_create_lisi", {"status": status, "entry_id": lisi_id})

        status, body = _request(
            client,
            "POST",
            "/api/v2/stories",
            payload={"world_id": world_id, "title": story_title, "metadata": {"creation_mode": "improv"}},
        )
        story_id = body.get("id") if isinstance(body, dict) else None
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

        base_payload = {
            "session_id": session_id,
            "story_id": story_id,
            "world_id": world_id,
            "provider": PROVIDER,
            "model": MODEL,
            "mode": "narrative",
            "temperature": 0.4,
            "max_tokens": 260,
            "creation_mode": "improv",
            "progress_intent": "hold",
        }

        round1_input = (
            "张三和李四在钟楼顶层会合。"
            "张三受伤但警觉地拿着铜钥匙，李四紧张地拿着火折子。"
            "张三决定寻找机关入口。"
        )
        status, generate_round1 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={**base_payload, "user_input": round1_input},
            with_user=True,
        )
        round1_updates = list(generate_round1.get("memory_updates") or []) if isinstance(generate_round1, dict) else []
        round1_snapshot = generate_round1.get("entity_state_snapshot") if isinstance(generate_round1, dict) else None
        round1_items = _extract_items_from_snapshot(round1_snapshot)
        zhangsan_round1 = _find_entity(round1_items, "张三")
        lisi_round1 = _find_entity(round1_items, "李四")

        _add(
            checks,
            status == 200 and isinstance(round1_snapshot, dict) and len(round1_items) >= 2,
            "generate_response_entity_snapshot",
            {
                "status": status,
                "snapshot_total": len(round1_items),
                "zhangsan": zhangsan_round1,
                "lisi": lisi_round1,
            },
        )
        _add(
            checks,
            _has_entity_update(round1_updates, source="generate"),
            "generate_memory_updates_contains_entity_state",
            {
                "memory_updates": round1_updates,
            },
        )

        episodic_ops = _operation_ids(round1_updates, "episodic")
        entity_ops = _operation_ids(round1_updates, "entity_state")
        shared_ops = sorted(episodic_ops.intersection(entity_ops))
        _add(
            checks,
            bool(shared_ops),
            "generate_operation_chain_aligned",
            {
                "episodic_operation_ids": sorted(episodic_ops),
                "entity_operation_ids": sorted(entity_ops),
                "shared_operation_ids": shared_ops,
            },
        )

        status, session_entity = _request(client, "GET", f"/api/v2/story/session/{session_id}/entity-state")
        session_items = list(session_entity.get("items") or []) if isinstance(session_entity, dict) else []
        session_zhangsan = _find_entity([item for item in session_items if isinstance(item, dict)], "张三")
        _add(
            checks,
            status == 200 and len(session_items) >= 2 and isinstance(session_zhangsan, dict),
            "session_entity_state_read",
            {
                "status": status,
                "total": len(session_items),
                "zhangsan": session_zhangsan,
            },
        )

        status, story_entity = _request(client, "GET", f"/api/v2/stories/{story_id}/entity-state")
        story_items = list(story_entity.get("items") or []) if isinstance(story_entity, dict) else []
        story_zhangsan = _find_entity([item for item in story_items if isinstance(item, dict)], "张三")
        _add(
            checks,
            status == 200 and len(story_items) >= 2 and isinstance(story_zhangsan, dict),
            "story_entity_state_read",
            {
                "status": status,
                "total": len(story_items),
                "zhangsan": story_zhangsan,
            },
        )

        status, timeline_before_stream = _request(
            client,
            "GET",
            f"/api/v2/story/session/{session_id}/memory-updates?page=1&page_size=200",
        )
        timeline_items_before = list(timeline_before_stream.get("items") or []) if isinstance(timeline_before_stream, dict) else []
        has_generate_entity_timeline = any(
            isinstance(item, dict)
            and item.get("memory_layer") == "entity_state"
            and item.get("source") == "generate"
            for item in timeline_items_before
        )
        _add(
            checks,
            status == 200 and has_generate_entity_timeline,
            "timeline_contains_generate_entity_events",
            {
                "status": status,
                "entity_sources": sorted(_timeline_entity_sources([item for item in timeline_items_before if isinstance(item, dict)])),
            },
        )

        stream_input = (
            "张三和李四赶到地下仓库。"
            "张三丢下了铜钥匙，李四警觉地握着火折子。"
            "张三准备封住入口。"
        )
        stream_status, stream_done, stream_chunks = _stream_generate(
            client,
            {**base_payload, "user_input": stream_input, "temperature": 0.5},
            with_user=True,
        )
        stream_snapshot = stream_done.get("entity_state_snapshot") if isinstance(stream_done, dict) else None
        stream_items = _extract_items_from_snapshot(stream_snapshot)
        zhangsan_stream = _find_entity(stream_items, "张三")
        _add(
            checks,
            stream_status == 200 and isinstance(stream_snapshot, dict) and bool(stream_done.get("done") is True or stream_done),
            "stream_done_contains_entity_snapshot",
            {
                "status": stream_status,
                "chunk_count": stream_chunks,
                "snapshot_total": len(stream_items),
            },
        )

        stream_location = str((zhangsan_stream or {}).get("current_location") or "")
        stream_inventory = list((zhangsan_stream or {}).get("inventory") or [])
        _add(
            checks,
            isinstance(zhangsan_stream, dict)
            and stream_location == "地下仓库"
            and "铜钥匙" not in stream_inventory,
            "stream_state_transition_applied",
            {
                "zhangsan": zhangsan_stream,
                "stream_done_preview": str(stream_done.get("generated_text") or stream_done.get("output_text") or "")[:180],
            },
        )

        status, rollback_body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
        rollback_updates = list(rollback_body.get("memory_updates") or []) if isinstance(rollback_body, dict) else []
        _add(
            checks,
            status == 200 and bool(rollback_body.get("deleted")),
            "rollback_delete_last_message",
            {"status": status, "body": rollback_body},
        )
        _add(
            checks,
            _has_entity_update(rollback_updates, source="rollback"),
            "rollback_rebuilds_entity_state",
            {"memory_updates": rollback_updates},
        )

        status, session_after_rollback = _request(client, "GET", f"/api/v2/story/session/{session_id}/entity-state")
        _add(
            checks,
            status == 200 and isinstance(session_after_rollback.get("total"), int),
            "session_entity_state_read_after_rollback",
            {"status": status, "body": session_after_rollback},
        )

        regenerate_payload = {
            "story_id": story_id,
            "provider": PROVIDER,
            "model": MODEL,
            "mode": "narrative",
            "temperature": 0.5,
            "max_tokens": 260,
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
        regenerate_updates = list(regenerate_body.get("memory_updates") or []) if isinstance(regenerate_body, dict) else []
        _add(
            checks,
            status == 200 and isinstance(regenerate_snapshot, dict),
            "regenerate_response_entity_snapshot",
            {
                "status": status,
                "snapshot_total": len(_extract_items_from_snapshot(regenerate_snapshot)),
            },
        )
        _add(
            checks,
            _has_entity_update(regenerate_updates),
            "regenerate_memory_updates_contains_entity_state",
            {
                "memory_updates": regenerate_updates,
            },
        )

        status, session_rebuild = _request(
            client,
            "POST",
            f"/api/v2/story/session/{session_id}/entity-state/rebuild?story_id={story_id}&world_id={world_id}",
        )
        session_rebuild_updates = list(session_rebuild.get("memory_updates") or []) if isinstance(session_rebuild, dict) else []
        _add(
            checks,
            status == 200
            and bool(session_rebuild.get("rebuilt"))
            and int(session_rebuild.get("entity_count") or 0) >= 1
            and _has_entity_update(session_rebuild_updates, source="entity_state_session_rebuild_api"),
            "session_entity_rebuild_api",
            {
                "status": status,
                "body": session_rebuild,
            },
        )

        segment1_prompt = "张三和李四在钟楼顶层，张三拿着铜钥匙。"
        segment1_content = "张三受伤但警觉，李四紧张地观察门口。张三决定寻找机关入口。"
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

        segment2_prompt = "张三和李四转入地下仓库，张三丢下了铜钥匙。"
        segment2_content = "地下仓库里回声沉重，李四警觉地握着火折子。"
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
            {
                "segment2_id": segment2_id,
            },
        )

        committed_segment2_content = (
            "张三和李四在地下仓库继续搜查。"
            "张三受伤但警觉，张三丢下了铜钥匙后准备封住入口。"
        )
        status, adjustment_commit = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/adjustments/commit",
            payload={
                "session_id": session_id,
                "updates": [
                    {
                        "segment_id": segment2_id,
                        "content": committed_segment2_content,
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
            "story_adjustment_commit_entity_updates",
            {
                "memory_updates": adjustment_updates,
            },
        )

        status, story_entity_after_commit = _request(client, "GET", f"/api/v2/stories/{story_id}/entity-state")
        commit_items = [item for item in list(story_entity_after_commit.get("items") or []) if isinstance(item, dict)]
        zhangsan_after_commit = _find_entity(commit_items, "张三")
        _add(
            checks,
            status == 200
            and isinstance(zhangsan_after_commit, dict)
            and str(zhangsan_after_commit.get("current_location") or "") == "地下仓库"
            and "铜钥匙" not in list(zhangsan_after_commit.get("inventory") or []),
            "story_entity_state_after_commit",
            {
                "status": status,
                "zhangsan": zhangsan_after_commit,
            },
        )

        status, segment_rollback = _request(client, "DELETE", f"/api/v2/stories/{story_id}/segments/last")
        segment_rollback_updates = list(segment_rollback.get("memory_updates") or []) if isinstance(segment_rollback, dict) else []
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
            "story_segment_rollback_entity_updates",
            {
                "memory_updates": segment_rollback_updates,
            },
        )

        status, story_entity_after_segment_rollback = _request(client, "GET", f"/api/v2/stories/{story_id}/entity-state")
        rollback_items = [item for item in list(story_entity_after_segment_rollback.get("items") or []) if isinstance(item, dict)]
        zhangsan_after_segment_rollback = _find_entity(rollback_items, "张三")
        _add(
            checks,
            status == 200
            and isinstance(zhangsan_after_segment_rollback, dict)
            and str(zhangsan_after_segment_rollback.get("current_location") or "") == "钟楼顶层"
            and "铜钥匙" in list(zhangsan_after_segment_rollback.get("inventory") or []),
            "story_entity_state_after_segment_rollback",
            {
                "status": status,
                "zhangsan": zhangsan_after_segment_rollback,
            },
        )

        status, story_rebuild = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/entity-state/rebuild?session_id={session_id}",
        )
        story_rebuild_updates = list(story_rebuild.get("memory_updates") or []) if isinstance(story_rebuild, dict) else []
        _add(
            checks,
            status == 200
            and bool(story_rebuild.get("rebuilt"))
            and int(story_rebuild.get("entity_count") or 0) >= 1
            and _has_entity_update(story_rebuild_updates, source="entity_state_story_rebuild_api"),
            "story_entity_rebuild_api",
            {
                "status": status,
                "body": story_rebuild,
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
            "rollback",
            "regenerate",
            "story_adjustment_commit",
            "story_segment_rollback",
            "entity_state_session_rebuild_api",
            "entity_state_story_rebuild_api",
        }
        missing_sources = sorted(required_sources - entity_sources)
        _add(
            checks,
            status == 200 and not missing_sources,
            "timeline_contains_entity_sources",
            {
                "status": status,
                "entity_sources": sorted(entity_sources),
                "missing_sources": missing_sources,
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
            "round1_snapshot": round1_snapshot,
            "stream_snapshot": stream_snapshot,
            "post_commit_story_snapshot": story_entity_after_commit,
            "post_story_rollback_snapshot": story_entity_after_segment_rollback,
            "final_timeline_entity_sources": sorted(entity_sources),
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
