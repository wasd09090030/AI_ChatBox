"""
Smoke validation runner for Plan_2026-03-28 dual-mode story creation.

Goals:
1) Validate scripted mode stage/event progression across a 4-phase full script.
2) Validate prompt focus adjustment effectiveness using keyword-differential checks.
3) Validate dual-mode branching signals (scripted vs improv response shape).

Usage:
  python scripts/smoke_dual_mode_plan_20260328.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8012
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
from typing import Any

import httpx

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8012").rstrip("/")
USER_ID = os.getenv("SMOKE_USER_ID", "user_1773820783085_bk1gzshza")
PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek")
MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat")
TIMEOUT = 180.0
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "TestResult"
REPORT_JSON = REPORT_DIR / "Plan0328_DualMode_Validation_Run.json"


@dataclass
class Check:
    name: str
    passed: bool
    detail: dict[str, Any]


def _headers() -> dict[str, str]:
    return {"X-User-ID": USER_ID}


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    with_user: bool = False,
) -> tuple[int, dict[str, Any]]:
    headers = _headers() if with_user else {}
    response = client.request(method.upper(), f"{BASE_URL}{path}", json=payload, headers=headers)
    try:
        body = response.json() if response.text else {}
    except Exception:
        body = {"raw": response.text}
    return response.status_code, body


def _add(checks: list[Check], cond: bool, name: str, detail: dict[str, Any]) -> None:
    checks.append(Check(name=name, passed=bool(cond), detail=detail))


def _extract_runtime(response: dict[str, Any]) -> dict[str, Any]:
    runtime = response.get("runtime_state_snapshot")
    return runtime if isinstance(runtime, dict) else {}


def _keyword_score(text: str, keywords: list[str]) -> int:
    lower_text = (text or "").lower()
    seen = 0
    for item in keywords:
        if item.lower() in lower_text:
            seen += 1
    return seen


def _preflight(client: httpx.Client, checks: list[Check]) -> None:
    status, body = _request(client, "GET", "/api/v2/health")
    _add(checks, status == 200 and body.get("status") == "healthy", "health", {"status": status, "body": body})

    status, body = _request(client, "GET", "/api/v2/providers", with_user=True)
    providers = {x.get("provider"): x for x in body.get("providers", [])} if status == 200 else {}
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
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        _preflight(client, checks)

        suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        world_name = f"Plan0328-双模式验证-{suffix}"
        story_title = "雾港四幕：潮线账本"

        # 4-phase complete script blueprint.
        stage1_id = f"stage-1-{uuid.uuid4().hex[:8]}"
        stage2_id = f"stage-2-{uuid.uuid4().hex[:8]}"
        stage3_id = f"stage-3-{uuid.uuid4().hex[:8]}"
        stage4_id = f"stage-4-{uuid.uuid4().hex[:8]}"

        event1_id = f"event-1-{uuid.uuid4().hex[:8]}"
        event2_id = f"event-2-{uuid.uuid4().hex[:8]}"
        event3_id = f"event-3-{uuid.uuid4().hex[:8]}"
        event4_id = f"event-4-{uuid.uuid4().hex[:8]}"
        foreshadow_id = f"foreshadow-ledger-{uuid.uuid4().hex[:8]}"

        status, body = _request(
            client,
            "POST",
            "/api/v2/worlds",
            payload={"name": world_name, "description": "Plan 03-28 双模式验证世界", "genre": "mystery"},
        )
        world_id = body.get("id") if isinstance(body, dict) else None
        _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

        status, body = _request(
            client,
            "POST",
            "/api/v2/script-designs",
            payload={
                "world_id": world_id,
                "title": "雾港潮线账本（四幕剧本）",
                "summary": "学徒调查潮汐账本，在灯塔对峙并回收伏笔。",
                "theme": "真相与代价",
                "core_conflict": "公开账本真相会引发港务系统动荡",
                "status": "active",
                "stage_outlines": [
                    {
                        "id": stage1_id,
                        "order": 1,
                        "title": "第一幕：雨夜入港",
                        "goal": "建立危机与核心谜题",
                        "tension": "异常潮汐与失踪记录",
                        "exit_condition": "主角确认账本线索可信",
                    },
                    {
                        "id": stage2_id,
                        "order": 2,
                        "title": "第二幕：账本解码",
                        "goal": "解出加密页码并定位灯塔",
                        "tension": "线索真假难辨",
                        "exit_condition": "确认对峙地点与时间",
                    },
                    {
                        "id": stage3_id,
                        "order": 3,
                        "title": "第三幕：灯塔对峙",
                        "goal": "与港务长正面冲突",
                        "tension": "证据可能被毁",
                        "exit_condition": "拿到可公开证据",
                    },
                    {
                        "id": stage4_id,
                        "order": 4,
                        "title": "第四幕：破晓收束",
                        "goal": "公布真相并给出代价",
                        "tension": "真相公开后的后果",
                        "exit_condition": "伏笔回收并完成主线",
                    },
                ],
                "event_nodes": [
                    {
                        "id": event1_id,
                        "stage_id": stage1_id,
                        "order": 1,
                        "event_type": "setup",
                        "title": "拾得潮线账本",
                        "objective": "确认账本记录与失踪案有关",
                        "obstacle": "记录缺页且字迹被海水腐蚀",
                        "expected_outcome": "主角决定追查灯塔",
                        "foreshadow_ids": [foreshadow_id],
                    },
                    {
                        "id": event2_id,
                        "stage_id": stage2_id,
                        "order": 1,
                        "event_type": "reveal",
                        "title": "解码账本页码",
                        "objective": "解析账本中的潮汐密码",
                        "obstacle": "密文掺杂伪造条目",
                        "expected_outcome": "锁定灯塔地下仓库",
                        "prerequisite_event_ids": [event1_id],
                    },
                    {
                        "id": event3_id,
                        "stage_id": stage3_id,
                        "order": 1,
                        "event_type": "conflict",
                        "title": "灯塔仓库对峙",
                        "objective": "阻止证据焚毁",
                        "obstacle": "港务长提前设伏",
                        "expected_outcome": "保住关键账页",
                        "prerequisite_event_ids": [event2_id],
                    },
                    {
                        "id": event4_id,
                        "stage_id": stage4_id,
                        "order": 1,
                        "event_type": "climax",
                        "title": "黎明公证",
                        "objective": "公开账本真相并承担代价",
                        "obstacle": "港口将爆发罢工与报复",
                        "expected_outcome": "主线收束并回收伏笔",
                        "prerequisite_event_ids": [event3_id],
                        "foreshadow_ids": [foreshadow_id],
                    },
                ],
                "foreshadows": [
                    {
                        "id": foreshadow_id,
                        "title": "潮线缺页",
                        "content": "账本缺失页在结尾揭示失踪真相",
                        "category": "mystery",
                        "planted_stage_id": stage1_id,
                        "planted_event_id": event1_id,
                        "expected_payoff_stage_id": stage4_id,
                        "expected_payoff_event_id": event4_id,
                        "payoff_description": "缺页作为关键证据公证",
                    }
                ],
                "default_generation_policy": {
                    "enforce_stage_order": True,
                    "enforce_pending_event": True,
                    "enforce_foreshadow_tracking": True,
                    "preferred_stage_id": stage1_id,
                    "preferred_event_ids": [event1_id],
                },
            },
        )
        script_design_id = body.get("id") if isinstance(body, dict) else None
        _add(
            checks,
            status == 200 and bool(script_design_id),
            "script_design_create",
            {"status": status, "script_design_id": script_design_id},
        )

        status, body = _request(
            client,
            "POST",
            "/api/v2/stories",
            payload={
                "world_id": world_id,
                "title": story_title,
                "metadata": {
                    "script_design_id": script_design_id,
                    "active_stage_id": stage1_id,
                    "active_event_id": event1_id,
                    "follow_script_design": True,
                    "creation_mode": "scripted",
                },
            },
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

        status, runtime_initial = _request(client, "GET", f"/api/v2/stories/{story_id}/runtime")
        _add(
            checks,
            status == 200 and runtime_initial.get("current_event_id") == event1_id,
            "runtime_init",
            {
                "status": status,
                "current_stage_id": runtime_initial.get("current_stage_id"),
                "current_event_id": runtime_initial.get("current_event_id"),
            },
        )

        scripted_base_payload: dict[str, Any] = {
            "session_id": session_id,
            "story_id": story_id,
            "world_id": world_id,
            "provider": PROVIDER,
            "model": MODEL,
            "mode": "narrative",
            "temperature": 0.7,
            "max_tokens": 320,
            "creation_mode": "scripted",
            "allow_state_transition": True,
            "script_design_id": script_design_id,
            "follow_script_design": True,
        }

        # 第一阶段 hold：预期不发生迁移。
        status, hold_p1 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第一幕：写主角在雨夜码头发现账本的瞬间。",
                "progress_intent": "hold",
                "active_stage_id": stage1_id,
                "active_event_id": event1_id,
                "focus_label": "环境描写",
                "focus_instruction": "突出潮声、雨滴、煤油灯三类感官细节。",
            },
            with_user=True,
        )
        runtime_hold_p1 = _extract_runtime(hold_p1)
        consistency_hold_p1 = hold_p1.get("consistency_check")
        _add(
            checks,
            status == 200
            and runtime_hold_p1.get("current_event_id") == event1_id
            and isinstance(consistency_hold_p1, dict)
            and consistency_hold_p1.get("passed") is True,
            "scripted_hold_no_transition",
            {
                "status": status,
                "current_event_id": runtime_hold_p1.get("current_event_id"),
                "consistency_check": consistency_hold_p1,
            },
        )

        # 第一阶段 complete：应推进到第二阶段。
        status, complete_p1 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第一幕收束：让主角确认账本是真实线索并决定前往灯塔。",
                "progress_intent": "complete",
                "active_stage_id": stage1_id,
                "active_event_id": event1_id,
                "focus_label": "决策节点",
                "focus_instruction": "明确写出‘决定去灯塔’这个动作结论。",
            },
            with_user=True,
        )
        runtime_complete_p1 = _extract_runtime(complete_p1)
        _add(
            checks,
            status == 200
            and runtime_complete_p1.get("current_event_id") == event2_id
            and event1_id in list(runtime_complete_p1.get("completed_event_ids") or []),
            "scripted_complete_phase1_progress",
            {
                "status": status,
                "runtime": runtime_complete_p1,
            },
        )

        # 第二阶段聚焦 A/B 对比。
        # 使用同义词感知关键词组，降低同义改写带来的误判。
        phase2_focus_a = ["钟声", "座钟", "潮湿", "海盐", "铁锈", "回声", "空廊"]
        phase2_focus_b = ["密码", "密文", "页码", "符号", "译码", "坐标", "重排"]

        status, p2_focus_a_resp = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第二幕：只描写主角在灯塔档案室的环境与氛围，不展开解码过程。",
                "progress_intent": "hold",
                "active_stage_id": stage2_id,
                "active_event_id": event2_id,
                "focus_label": "环境压迫",
                "focus_instruction": "重点写环境压迫感：钟声、潮湿墙面、铁锈味、空廊回声；避免出现密码、页码、符号、译码等技术术语。",
                "temperature": 0.2,
            },
            with_user=True,
        )
        p2_text_a = str(p2_focus_a_resp.get("output_text") or "")
        score_a_on_a = _keyword_score(p2_text_a, phase2_focus_a)
        score_b_on_a = _keyword_score(p2_text_a, phase2_focus_b)

        status_b, p2_focus_b_resp = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第二幕：直接展示账本解码步骤和结论，不做环境渲染。",
                "progress_intent": "hold",
                "active_stage_id": stage2_id,
                "active_event_id": event2_id,
                "focus_label": "解码逻辑",
                "focus_instruction": "重点写解码过程：密码位移、页码重排、符号对应、译码结论；尽量减少环境描写。",
                "temperature": 0.2,
            },
            with_user=True,
        )
        p2_text_b = str(p2_focus_b_resp.get("output_text") or "")
        score_a_on_b = _keyword_score(p2_text_b, phase2_focus_a)
        score_b_on_b = _keyword_score(p2_text_b, phase2_focus_b)

        prompt_focus_effective = (
            status == 200
            and status_b == 200
            and score_a_on_a > score_a_on_b
            and score_b_on_b > score_b_on_a
        )
        _add(
            checks,
            prompt_focus_effective,
            "prompt_focus_shift_effective",
            {
                "status_a": status,
                "status_b": status_b,
                "focus_a_keywords": phase2_focus_a,
                "focus_b_keywords": phase2_focus_b,
                "score_a_on_a": score_a_on_a,
                "score_b_on_a": score_b_on_a,
                "score_a_on_b": score_a_on_b,
                "score_b_on_b": score_b_on_b,
                "sample_a": p2_text_a[:260],
                "sample_b": p2_text_b[:260],
            },
        )

        # 第二阶段 complete -> 第三阶段。
        status, complete_p2 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第二幕收束：锁定灯塔地下仓库并准备行动。",
                "progress_intent": "complete",
                "active_stage_id": stage2_id,
                "active_event_id": event2_id,
                "focus_label": "阶段推进",
                "focus_instruction": "给出明确行动计划，收束解码过程。",
            },
            with_user=True,
        )
        runtime_complete_p2 = _extract_runtime(complete_p2)
        _add(
            checks,
            status == 200
            and runtime_complete_p2.get("current_event_id") == event3_id
            and event2_id in list(runtime_complete_p2.get("completed_event_ids") or []),
            "scripted_complete_phase2_progress",
            {"status": status, "runtime": runtime_complete_p2},
        )

        # 第三阶段 advance：不应自动完成当前事件。
        status, advance_p3 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第三幕推进：在灯塔仓库与港务长短兵相接。",
                "progress_intent": "advance",
                "active_stage_id": stage3_id,
                "active_event_id": event3_id,
                "focus_label": "冲突升温",
                "focus_instruction": "强化对峙和风险，不要立刻结案。",
            },
            with_user=True,
        )
        runtime_advance_p3 = _extract_runtime(advance_p3)
        completed_after_advance = list(runtime_advance_p3.get("completed_event_ids") or [])
        _add(
            checks,
            status == 200
            and runtime_advance_p3.get("current_event_id") == event3_id
            and event3_id not in completed_after_advance,
            "scripted_advance_no_complete",
            {"status": status, "runtime": runtime_advance_p3},
        )

        # 第三阶段 complete -> 第四阶段。
        status, complete_p3 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第三幕收束：保住关键账页并逼退对手。",
                "progress_intent": "complete",
                "active_stage_id": stage3_id,
                "active_event_id": event3_id,
                "focus_label": "证据保全",
                "focus_instruction": "写清楚‘关键账页得以保留’这一结果。",
            },
            with_user=True,
        )
        runtime_complete_p3 = _extract_runtime(complete_p3)
        _add(
            checks,
            status == 200 and runtime_complete_p3.get("current_event_id") == event4_id,
            "scripted_complete_phase3_progress",
            {"status": status, "runtime": runtime_complete_p3},
        )

        # 第四阶段 complete：停留在最终事件并标记完成。
        status, complete_p4 = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                **scripted_base_payload,
                "user_input": "第四幕收束：黎明公证，公开真相并承担后果。",
                "progress_intent": "complete",
                "active_stage_id": stage4_id,
                "active_event_id": event4_id,
                "focus_label": "代价结局",
                "focus_instruction": "强调真相公开后的代价与人物选择。",
            },
            with_user=True,
        )
        runtime_complete_p4 = _extract_runtime(complete_p4)
        _add(
            checks,
            status == 200
            and runtime_complete_p4.get("current_event_id") == event4_id
            and event4_id in list(runtime_complete_p4.get("completed_event_ids") or []),
            "scripted_complete_final_phase",
            {"status": status, "runtime": runtime_complete_p4},
        )

        # 更新后计划验证：严格回滚链应移除已持久化段落，
        # 并将运行态恢复到上一快照 / 初始快照。
        status, _ = _request(
            client,
            "PUT",
            f"/api/v2/stories/{story_id}",
            payload={
                "metadata": {
                    "runtime_initial_snapshot": runtime_initial,
                }
            },
        )
        _add(checks, status == 200, "set_runtime_initial_snapshot", {"status": status})

        status_seg_1, _ = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/segments",
            payload={
                "prompt": "第三幕收束",
                "content": str(complete_p3.get("output_text") or ""),
                "retrieved_context": [],
                "runtime_state_snapshot": runtime_complete_p3,
            },
        )
        status_seg_2, _ = _request(
            client,
            "POST",
            f"/api/v2/stories/{story_id}/segments",
            payload={
                "prompt": "第四幕收束",
                "content": str(complete_p4.get("output_text") or ""),
                "retrieved_context": [],
                "runtime_state_snapshot": runtime_complete_p4,
            },
        )
        status_story, story_before_rb = _request(client, "GET", f"/api/v2/stories/{story_id}")
        before_count = len(list((story_before_rb or {}).get("segments") or []))
        _add(
            checks,
            status_seg_1 == 200 and status_seg_2 == 200 and status_story == 200 and before_count >= 2,
            "seed_segments_for_rollback",
            {
                "status_seg_1": status_seg_1,
                "status_seg_2": status_seg_2,
                "status_story": status_story,
                "segment_count_before": before_count,
            },
        )

        status_rb1, rb1_body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
        _add(
            checks,
            status_rb1 == 200 and bool((rb1_body or {}).get("deleted")),
            "session_rollback_step1",
            {"status": status_rb1, "body": rb1_body},
        )

        status_del_seg_1, del_seg_1_body = _request(client, "DELETE", f"/api/v2/stories/{story_id}/segments/last")
        rb1_story = (del_seg_1_body or {}).get("story") if isinstance(del_seg_1_body, dict) else {}
        rb1_runtime = (del_seg_1_body or {}).get("runtime_state") if isinstance(del_seg_1_body, dict) else {}
        rb1_count = len(list((rb1_story or {}).get("segments") or [])) if isinstance(rb1_story, dict) else -1
        expected_prev_event = runtime_complete_p3.get("current_event_id")
        _add(
            checks,
            status_del_seg_1 == 200
            and rb1_count == max(0, before_count - 1)
            and isinstance(rb1_runtime, dict)
            and rb1_runtime.get("current_event_id") == expected_prev_event,
            "strict_rollback_restore_previous_runtime",
            {
                "status": status_del_seg_1,
                "segment_count_after": rb1_count,
                "expected_prev_event": expected_prev_event,
                "runtime_state": rb1_runtime,
            },
        )

        status_rb2, rb2_body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
        _add(
            checks,
            status_rb2 == 200 and bool((rb2_body or {}).get("deleted")),
            "session_rollback_step2",
            {"status": status_rb2, "body": rb2_body},
        )

        status_del_seg_2, del_seg_2_body = _request(client, "DELETE", f"/api/v2/stories/{story_id}/segments/last")
        rb2_story = (del_seg_2_body or {}).get("story") if isinstance(del_seg_2_body, dict) else {}
        rb2_runtime = (del_seg_2_body or {}).get("runtime_state") if isinstance(del_seg_2_body, dict) else {}
        rb2_count = len(list((rb2_story or {}).get("segments") or [])) if isinstance(rb2_story, dict) else -1
        expected_initial_event = runtime_initial.get("current_event_id")
        _add(
            checks,
            status_del_seg_2 == 200
            and rb2_count == max(0, before_count - 2)
            and isinstance(rb2_runtime, dict)
            and rb2_runtime.get("current_event_id") == expected_initial_event,
            "strict_rollback_restore_initial_runtime",
            {
                "status": status_del_seg_2,
                "segment_count_after": rb2_count,
                "expected_initial_event": expected_initial_event,
                "runtime_state": rb2_runtime,
            },
        )

        # 使用同一 story/session 做双模式分支检查。
        status, improv_resp = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                "session_id": session_id,
                "story_id": story_id,
                "world_id": world_id,
                "provider": PROVIDER,
                "model": MODEL,
                "mode": "narrative",
                "temperature": 0.7,
                "max_tokens": 260,
                "creation_mode": "improv",
                "progress_intent": "hold",
                "user_input": "以即兴模式写一个主角在港口短暂停留的片段。",
                "focus_instruction": "强调即兴感和人物即时反应。",
            },
            with_user=True,
        )
        _add(
            checks,
            status == 200
            and improv_resp.get("creation_mode") == "improv"
            and improv_resp.get("consistency_check") is None,
            "dual_mode_branching",
            {
                "status": status,
                "creation_mode": improv_resp.get("creation_mode"),
                "consistency_check": improv_resp.get("consistency_check"),
            },
        )

        evidence = {
            "world_id": world_id,
            "story_id": story_id,
            "session_id": session_id,
            "script_design_id": script_design_id,
            "phase_ids": {
                "stage_ids": [stage1_id, stage2_id, stage3_id, stage4_id],
                "event_ids": [event1_id, event2_id, event3_id, event4_id],
                "foreshadow_id": foreshadow_id,
            },
            "prompt_focus_scores": {
                "score_a_on_a": score_a_on_a,
                "score_b_on_a": score_b_on_a,
                "score_a_on_b": score_a_on_b,
                "score_b_on_b": score_b_on_b,
            },
            "rollback_validation": {
                "segments_before": before_count,
                "segments_after_first_rollback": rb1_count,
                "segments_after_second_rollback": rb2_count,
                "expected_previous_event": expected_prev_event,
                "expected_initial_event": expected_initial_event,
                "restored_event_after_first_rollback": (
                    rb1_runtime.get("current_event_id") if isinstance(rb1_runtime, dict) else None
                ),
                "restored_event_after_second_rollback": (
                    rb2_runtime.get("current_event_id") if isinstance(rb2_runtime, dict) else None
                ),
            },
            "final_runtime": runtime_complete_p4,
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
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nReport written: {REPORT_JSON}")


if __name__ == "__main__":
    main()
