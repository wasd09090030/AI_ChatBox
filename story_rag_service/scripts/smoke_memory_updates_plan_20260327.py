"""
Unified smoke runner for Plan_2026-03-27.

Profiles:
  - A: contract + consistency baseline chain
  - B: semantic-focused chain
  - all: run A then B

Usage:
  python scripts/smoke_memory_updates_plan_20260327.py --profile A
  python scripts/smoke_memory_updates_plan_20260327.py --profile B
  python scripts/smoke_memory_updates_plan_20260327.py --profile all

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8012
  SMOKE_USER_ID=user_xxx
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# 统一服务地址，允许通过环境变量切换到远端或本地实例。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8012").rstrip("/")
# 为请求统一附带用户头，确保命中用户级配置读取路径。
USER_ID = os.getenv("SMOKE_USER_ID", "user_1773820783085_bk1gzshza")
# 指定冒烟运行使用的模型提供商。
PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek")
# 指定冒烟运行使用的模型名称。
MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat")
# 本地 SQLite 路径，用于读取摘要与消息数量证据。
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "chatbox.db"
# 为 HTTP 请求设置统一超时时间，避免脚本无限阻塞。
TIMEOUT = 120.0


@dataclass
class Check:
    """单项检查结果，包含名称、是否通过与证据细节。"""
    name: str
    passed: bool
    detail: dict[str, Any]


def _headers() -> dict[str, str]:
    """构造统一请求头。"""
    return {"X-User-ID": USER_ID}


def _request(client: httpx.Client, method: str, path: str, payload: dict[str, Any] | None = None, with_user: bool = False) -> tuple[int, dict[str, Any]]:
    """统一封装 HTTP 请求并容错解析 JSON 响应体。"""
    headers = _headers() if with_user else {}
    resp = client.request(method.upper(), f"{BASE_URL}{path}", json=payload, headers=headers)
    try:
        body = resp.json() if resp.text else {}
    except Exception:
        body = {"raw": resp.text}
    return resp.status_code, body


def _summary_row(session_id: str) -> dict[str, Any]:
    """读取会话摘要表最近一条记录，用于验证语义层是否重建。"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        "SELECT summary_text, updated_at FROM conversation_summaries WHERE session_id=? ORDER BY updated_at DESC LIMIT 1",
        (session_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"exists": False, "summary_text": None, "updated_at": None}
    text = row[0] or ""
    return {"exists": bool(text.strip()), "summary_text": text, "updated_at": row[1]}


def _message_count(session_id: str) -> int:
    """读取会话消息总数，辅助校验回滚/重建后的持久化状态。"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM story_session_messages WHERE session_id=?", (session_id,))
    count = int(cur.fetchone()[0])
    conn.close()
    return count


def _journal_tail(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """读取 memory_update_journal 最近事件，作为链路证据输出。"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        "SELECT memory_layer, action, source, status, committed_at FROM memory_update_journal WHERE session_id=? ORDER BY committed_at DESC LIMIT ?",
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "memory_layer": r[0],
            "action": r[1],
            "source": r[2],
            "status": r[3],
            "committed_at": r[4],
        }
        for r in rows
    ]


def _event_actions(events: list[dict[str, Any]] | None) -> list[str]:
    """将内存更新事件压平成 action 字符串，便于断言匹配。"""
    return [f"{e.get('memory_layer')}:{e.get('action')}:{e.get('source')}" for e in (events or [])]


def _add(checks: list[Check], cond: bool, name: str, detail: dict[str, Any]) -> None:
    """追加单项检查结果。"""
    checks.append(Check(name=name, passed=bool(cond), detail=detail))


def _preflight(client: httpx.Client, checks: list[Check]) -> None:
    """执行健康检查、Provider 可用性与连通性前置验证。"""
    status, body = _request(client, "GET", "/api/v2/health")
    _add(checks, status == 200 and body.get("status") == "healthy", "health", {"status": status, "body": body})

    status, body = _request(client, "GET", "/api/v2/providers", with_user=True)
    providers = {x.get("provider"): x for x in body.get("providers", [])} if status == 200 else {}
    deepseek_ok = bool(providers.get(PROVIDER, {}).get("available"))
    _add(checks, status == 200 and deepseek_ok, "providers_ready", {"status": status, "provider": providers.get(PROVIDER)})

    status, body = _request(client, "POST", "/api/v2/providers/test-connection", payload={"provider": PROVIDER, "base_url": None}, with_user=True)
    _add(checks, status == 200 and body.get("success") is True, "provider_connection", {"status": status, "body": body})


def run_profile_a(client: httpx.Client) -> dict[str, Any]:
    """执行 A 链路：契约一致性与回滚/提交事件校验。"""
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    _preflight(client, checks)

    session_id = f"plan0327-a-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    evidence["session_id"] = session_id

    status, body = _request(client, "POST", "/api/v2/story/session", payload={"session_id": session_id}, with_user=True)
    _add(checks, status == 200 and body.get("session_id") == session_id, "session_create", {"status": status, "body": body})

    for i in range(1, 3):
        status, body = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                "session_id": session_id,
                "user_input": f"A链路第{i}轮：推进剧情。",
                "provider": PROVIDER,
                "model": MODEL,
                "mode": "narrative",
                "temperature": 0.7,
                "max_tokens": 220,
            },
            with_user=True,
        )
        actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
        _add(checks, status == 200 and any(a.startswith("episodic:updated:generate") for a in actions), f"generate_round_{i}", {"status": status, "actions": actions})

    cnt_after_gen = _message_count(session_id)
    _add(checks, cnt_after_gen >= 4, "db_after_generate", {"message_count": cnt_after_gen})

    status, body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
    rb_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    _add(
        checks,
        status == 200 and any(a.startswith("episodic:rebuilt:rollback") for a in rb_actions) and any(a.startswith("episodic:reindexed:rollback") for a in rb_actions),
        "rollback_contract",
        {"status": status, "actions": rb_actions},
    )

    status, body = _request(
        client,
        "POST",
        f"/api/v2/story/session/{session_id}/regenerate",
        payload={"provider": PROVIDER, "model": MODEL, "mode": "narrative", "temperature": 0.7, "max_tokens": 220},
        with_user=True,
    )
    rg_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    _add(
        checks,
        status == 200 and any(a.startswith("episodic:rebuilt:regenerate") for a in rg_actions) and any(a.startswith("episodic:reindexed:regenerate") for a in rg_actions),
        "regenerate_contract",
        {"status": status, "actions": rg_actions},
    )

    status, body = _request(
        client,
        "POST",
        "/api/v2/worlds",
        payload={"name": f"Plan0327-A-{uuid.uuid4().hex[:6]}", "description": "smoke", "genre": "mystery"},
    )
    world_id = body.get("id") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

    status, body = _request(client, "POST", "/api/v2/stories", payload={"world_id": world_id, "title": "A Story"})
    story_id = body.get("id") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(story_id), "story_create", {"status": status, "story_id": story_id})

    original_text = "主角在阁楼里找到一把铜钥匙。"
    status, body = _request(
        client,
        "POST",
        f"/api/v2/stories/{story_id}/segments",
        payload={"prompt": "继续", "content": original_text, "retrieved_context": []},
    )
    segments = body.get("segments", []) if isinstance(body, dict) else []
    segment_id = segments[-1]["id"] if segments else None
    _add(checks, status == 200 and bool(segment_id), "segment_create", {"status": status, "segment_id": segment_id})

    status, body = _request(
        client,
        "POST",
        "/api/v2/story/adjustments/polish",
        payload={
            "story_id": story_id,
            "session_id": session_id,
            "segment_id": segment_id,
            "selected_text": "铜钥匙",
            "before_context": "主角在阁楼里找到一把",
            "after_context": "。",
            "preset_key": "clarity_polish",
            "preset_instruction": "保持事实不变，提升细节",
            "provider": PROVIDER,
            "model": MODEL,
        },
        with_user=True,
    )
    polished = body.get("polished_text") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(polished), "polish", {"status": status, "polished_text": polished})

    status_story, story_before = _request(client, "GET", f"/api/v2/stories/{story_id}")
    before_text = ""
    if status_story == 200 and story_before.get("segments"):
        before_text = story_before["segments"][-1].get("content", "")
    _add(checks, before_text == original_text, "draft_only", {"before_text": before_text})

    new_text = original_text.replace("铜钥匙", polished or "锈蚀钥匙")
    status, body = _request(
        client,
        "POST",
        f"/api/v2/stories/{story_id}/adjustments/commit",
        payload={"session_id": f"commit-{session_id}", "updates": [{"segment_id": segment_id, "content": new_text}]},
    )
    cm_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    _add(
        checks,
        status == 200 and any(a.startswith("episodic:rebuilt:story_adjustment_commit") for a in cm_actions) and any(a.startswith("episodic:reindexed:story_adjustment_commit") for a in cm_actions),
        "commit_contract",
        {"status": status, "actions": cm_actions},
    )

    status_story, story_after = _request(client, "GET", f"/api/v2/stories/{story_id}")
    after_text = ""
    if status_story == 200 and story_after.get("segments"):
        after_text = story_after["segments"][-1].get("content", "")
    _add(checks, after_text == new_text, "commit_persisted", {"after_text": after_text})

    evidence["journal_tail"] = _journal_tail(session_id, 20)
    evidence["message_count"] = _message_count(session_id)

    return {
        "profile": "A",
        "checks": [c.__dict__ for c in checks],
        "evidence": evidence,
    }


def run_profile_b(client: httpx.Client) -> dict[str, Any]:
    """执行 B 链路：语义摘要生成、重置与恢复行为校验。"""
    checks: list[Check] = []
    evidence: dict[str, Any] = {}

    _preflight(client, checks)

    session_id = f"plan0327-b-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    evidence["session_id"] = session_id

    status, body = _request(client, "POST", "/api/v2/story/session", payload={"session_id": session_id}, with_user=True)
    _add(checks, status == 200 and body.get("session_id") == session_id, "session_create", {"status": status, "body": body})

    rounds: list[dict[str, Any]] = []
    summary_ready = False
    for i in range(1, 11):
        status, body = _request(
            client,
            "POST",
            "/api/v2/story/generate",
            payload={
                "session_id": session_id,
                "user_input": f"B链路第{i}轮：归纳线索并推进剧情。",
                "provider": PROVIDER,
                "model": MODEL,
                "mode": "narrative",
                "temperature": 0.7,
                "max_tokens": 240,
            },
            with_user=True,
        )
        summary = _summary_row(session_id)
        actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
        rounds.append({"round": i, "status": status, "summary_exists": summary["exists"], "actions": actions})
        if status == 200 and summary["exists"]:
            summary_ready = True
            break
    evidence["rounds"] = rounds

    _add(checks, summary_ready, "summary_materialized", {"rounds": rounds, "summary": _summary_row(session_id)})

    before_count = _message_count(session_id)
    status, body = _request(client, "DELETE", f"/api/v2/story/session/{session_id}/messages/last")
    rb_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    after_rb_summary = _summary_row(session_id)
    _add(
        checks,
        status == 200 and any(a.startswith("semantic:reset:rollback") for a in rb_actions) and not after_rb_summary["exists"],
        "rollback_semantic_reset",
        {"status": status, "actions": rb_actions, "summary_after": after_rb_summary, "before_count": before_count, "after_count": _message_count(session_id)},
    )

    status, body = _request(
        client,
        "POST",
        f"/api/v2/story/session/{session_id}/regenerate",
        payload={"provider": PROVIDER, "model": MODEL, "mode": "narrative", "temperature": 0.7, "max_tokens": 240},
        with_user=True,
    )
    rg_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    sum_after_regen = _summary_row(session_id)
    _add(
        checks,
        status == 200 and any(a.startswith("episodic:rebuilt:regenerate") for a in rg_actions),
        "regenerate_rebuild",
        {"status": status, "actions": rg_actions, "summary_after": sum_after_regen},
    )

    if not sum_after_regen["exists"]:
        for j in range(1, 4):
            _request(
                client,
                "POST",
                "/api/v2/story/generate",
                payload={
                    "session_id": session_id,
                    "user_input": f"B补充轮{j}：继续推进。",
                    "provider": PROVIDER,
                    "model": MODEL,
                    "mode": "narrative",
                    "temperature": 0.7,
                    "max_tokens": 220,
                },
                with_user=True,
            )
            if _summary_row(session_id)["exists"]:
                break

    _add(checks, _summary_row(session_id)["exists"], "summary_recovered_before_commit", {"summary": _summary_row(session_id)})

    status, body = _request(
        client,
        "POST",
        "/api/v2/worlds",
        payload={"name": f"Plan0327-B-{uuid.uuid4().hex[:6]}", "description": "semantic smoke", "genre": "mystery"},
    )
    world_id = body.get("id") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(world_id), "world_create", {"status": status, "world_id": world_id})

    status, body = _request(client, "POST", "/api/v2/stories", payload={"world_id": world_id, "title": "B Story"})
    story_id = body.get("id") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(story_id), "story_create", {"status": status, "story_id": story_id})

    original_text = "主角在旧仓库发现一本残缺日志。"
    status, body = _request(
        client,
        "POST",
        f"/api/v2/stories/{story_id}/segments",
        payload={"prompt": "继续", "content": original_text, "retrieved_context": []},
    )
    segments = body.get("segments", []) if isinstance(body, dict) else []
    segment_id = segments[-1]["id"] if segments else None
    _add(checks, status == 200 and bool(segment_id), "segment_create", {"status": status, "segment_id": segment_id})

    status, body = _request(
        client,
        "POST",
        "/api/v2/story/adjustments/polish",
        payload={
            "story_id": story_id,
            "session_id": session_id,
            "segment_id": segment_id,
            "selected_text": "残缺日志",
            "before_context": "主角在旧仓库发现一本",
            "after_context": "。",
            "preset_key": "clarity_polish",
            "preset_instruction": "保持事实，增强画面",
            "provider": PROVIDER,
            "model": MODEL,
        },
        with_user=True,
    )
    polished = body.get("polished_text") if isinstance(body, dict) else None
    _add(checks, status == 200 and bool(polished), "polish", {"status": status, "polished_text": polished})

    status, body = _request(
        client,
        "POST",
        f"/api/v2/stories/{story_id}/adjustments/commit",
        payload={
            "session_id": session_id,
            "updates": [{"segment_id": segment_id, "content": original_text.replace("残缺日志", polished or "破损日志")}],
        },
    )
    cm_actions = _event_actions(body.get("memory_updates") if isinstance(body, dict) else None)
    summary_after_commit = _summary_row(session_id)
    _add(
        checks,
        status == 200 and any(a.startswith("semantic:reset:story_adjustment_commit") for a in cm_actions) and not summary_after_commit["exists"],
        "commit_semantic_reset",
        {
            "status": status,
            "actions": cm_actions,
            "summary_after": summary_after_commit,
            "rebuild_summary_reset": body.get("rebuild_summary_reset") if isinstance(body, dict) else None,
            "rebuild_history_reindexed": body.get("rebuild_history_reindexed") if isinstance(body, dict) else None,
        },
    )

    evidence["journal_tail"] = _journal_tail(session_id, 30)

    return {
        "profile": "B",
        "checks": [c.__dict__ for c in checks],
        "evidence": evidence,
    }


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    """汇总单个 profile 的通过/失败统计。"""
    checks = result.get("checks", [])
    failed = [c for c in checks if not c.get("passed")]
    return {
        "profile": result.get("profile"),
        "total": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "failed_checks": [x.get("name") for x in failed],
    }


def main() -> int:
    """按参数执行 A/B/all 冒烟链路并输出汇总 JSON。"""
    parser = argparse.ArgumentParser(description="Unified smoke runner for Plan_2026-03-27")
    parser.add_argument("--profile", choices=["A", "B", "all"], default="all", help="Which profile to run")
    parser.add_argument("--output", default="", help="Optional file path for JSON output")
    args = parser.parse_args()

    all_results: dict[str, Any] = {
        "meta": {
            "base_url": BASE_URL,
            "user_id": USER_ID,
            "provider": PROVIDER,
            "model": MODEL,
            "profile": args.profile,
        },
        "runs": [],
    }

    with httpx.Client(timeout=TIMEOUT) as client:
        if args.profile in ("A", "all"):
            ra = run_profile_a(client)
            all_results["runs"].append({"result": ra, "summary": summarize(ra)})
        if args.profile in ("B", "all"):
            rb = run_profile_b(client)
            all_results["runs"].append({"result": rb, "summary": summarize(rb)})

    all_failed = 0
    for item in all_results["runs"]:
        all_failed += int(item["summary"]["failed"])

    all_results["overall"] = {
        "run_count": len(all_results["runs"]),
        "failed_checks": all_failed,
        "passed": all_failed == 0,
    }

    rendered = json.dumps(all_results, ensure_ascii=False, indent=2)
    print(rendered)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")

    return 1 if all_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
