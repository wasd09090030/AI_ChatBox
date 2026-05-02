"""上古卷轴世界运行级验证脚本。

目标：
1. 使用隔离 SQLite 副本启动本地 FastAPI 服务；
2. 复用数据库中的“上古卷轴”世界与 Lorebook 条目；
3. 创建临时测试账号并借用现有 DeepSeek 配置；
4. 执行不超过 6 轮的真实故事生成验证；
5. 自动输出 JSON / Markdown 测试报告。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

DEFAULT_WORLD_NAME = "上古卷轴"
DEFAULT_PORT = 8014
DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-chat"
MAX_ROUNDS = 6
ROUND_PROMPTS = [
    "我在海尔根囚车上醒来，四周都是帝国士兵和风暴斗篷俘虏。请直接描写押往处刑场的过程。",
    "混乱爆发后，我选择跟随拉罗夫逃跑，并询问他帝国与风暴斗篷冲突的核心原因。",
    "进入海尔根要塞后，我想先找一把武器和轻甲，再观察哈达瓦那一侧的动静。请延续上一轮。",
    "逃出海尔根后，请描写通往溪木镇前的夜路，并延续前文人物状态，不要重置情节。",
    "抵达溪木镇后，我想低调打听白漫城和巨龙袭击的消息，同时保留对海尔根灾难的余悸。",
    "夜晚休整时，请让拉罗夫或哈达瓦对我当前的选择作出回应，并推进下一步目标。",
]
PREFERRED_ENTRY_NAMES = [
    "【世界设定】上古卷轴",
    "海尔根监狱",
    "拉罗夫",
    "哈达瓦",
    "乌弗瑞克·风暴斗篷",
]


@dataclass
class ReportPaths:
    json_path: Path
    md_path: Path


@dataclass
class RuntimeContext:
    runtime_dir: Path
    database_path: Path
    port: int
    base_url: str
    server_log_path: Path


def _utc_like_timestamp() -> str:
    """生成用于文件名的本地时间戳。"""
    return time.strftime("%Y-%m-%d_%H-%M-%S")


def _require_ok(response: httpx.Response, label: str) -> Any:
    """要求响应为非错误状态，否则抛出异常。"""
    if response.status_code >= 400:
        raise RuntimeError(
            f"{label} failed: HTTP {response.status_code} -> {response.text[:1000]}"
        )
    return response.json()


def _write_report(report: dict[str, Any], paths: ReportPaths) -> None:
    """同时写入 JSON 与 Markdown 报告。"""
    paths.json_path.parent.mkdir(parents=True, exist_ok=True)
    paths.json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths.md_path.write_text(_render_markdown(report, paths), encoding="utf-8")


def _render_markdown(report: dict[str, Any], paths: ReportPaths) -> str:
    """将运行结果渲染为 Markdown 报告。"""
    summary = report.get("summary", {})
    world = report.get("world", {})
    rounds = list(report.get("rounds", []))
    checks = list(report.get("checks", []))
    findings = list(report.get("findings", []))
    errors = list(report.get("errors", []))

    lines: list[str] = []
    lines.append(f"# TES World Validation Report ({summary.get('executed_at', '-')})")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(f"- overall_status: {summary.get('overall_status', '-')}")
    lines.append(f"- base_url: {summary.get('base_url', '-')}")
    lines.append(f"- world_name: {world.get('name', '-')}")
    lines.append(f"- world_id: {world.get('world_id', '-')}")
    lines.append(f"- round_count: {summary.get('round_count', 0)}")
    lines.append(f"- report_json: {paths.json_path.as_posix()}")
    lines.append(f"- report_markdown: {paths.md_path.as_posix()}")
    lines.append("")
    lines.append("## 2. Functional Checks")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for item in checks:
        lines.append(
            f"| {item.get('name', '-')} | {item.get('status', '-')} | {str(item.get('detail', '-')).replace('|', '\\|')} |"
        )
    lines.append("")
    lines.append("## 3. Round Results")
    lines.append("")
    lines.append("| Round | Contexts | Output Chars | Token Source | Generation Time(s) | Segments After Append |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for item in rounds:
        lines.append(
            f"| {item.get('round')} | {item.get('contexts_count')} | {item.get('output_chars')} | "
            f"{item.get('token_source', '-')} | {item.get('generation_time', '-')} | {item.get('story_segments_after_append', '-')} |"
        )
    lines.append("")
    lines.append("## 4. Findings")
    lines.append("")
    if findings:
        for item in findings:
            lines.append(f"- {item}")
    else:
        lines.append("- No additional findings.")
    lines.append("")
    lines.append("## 5. Errors")
    lines.append("")
    if errors:
        for item in errors:
            lines.append(f"- {item}")
    else:
        lines.append("- No execution errors.")
    lines.append("")
    lines.append("## 6. Selected Lorebook Entries")
    lines.append("")
    for name in world.get("selected_entry_names", []):
        lines.append(f"- {name}")
    lines.append("")
    lines.append("## 7. Persistence Summary")
    lines.append("")
    lines.append(f"- final_story_segments: {report.get('persistence', {}).get('final_story_segments', '-')}")
    lines.append(f"- db_message_count: {report.get('persistence', {}).get('db_message_count', '-')}")
    lines.append(f"- db_memory_update_count: {report.get('persistence', {}).get('db_memory_update_count', '-')}")
    lines.append(f"- story_memory_timeline_total: {report.get('persistence', {}).get('story_memory_timeline_total', '-')}")
    return "\n".join(lines)


def _start_server(service_dir: Path, runtime: RuntimeContext) -> subprocess.Popen[str]:
    """使用当前虚拟环境启动本地 uvicorn 服务。"""
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(runtime.database_path)
    env["CHROMA_PERSIST_DIRECTORY"] = str(runtime.runtime_dir / "chroma_db")
    env["HUGGINGFACE_CACHE_DIR"] = str(runtime.runtime_dir / "hf_cache")
    env["LANGGRAPH_CHECKPOINT_SQLITE_PATH"] = str(runtime.runtime_dir / "langgraph_checkpoints.db")
    env["API_RELOAD"] = "false"
    env["ALLOW_ONLINE_EMBEDDING_DOWNLOAD"] = "false"

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with runtime.server_log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(runtime.port),
            ],
            cwd=str(service_dir),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
    return process


def _stop_server(process: Optional[subprocess.Popen[str]]) -> None:
    """安全停止后台服务。"""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_server(base_url: str, timeout_seconds: int) -> None:
    """轮询等待服务健康。"""
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/api/v2/health", timeout=5.0)
            if response.status_code == 200:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"Server not ready within {timeout_seconds}s: {last_error}")


def _load_provider_seed(database_path: Path) -> dict[str, str | None]:
    """读取一条可用的 DeepSeek 用户级配置作为种子。"""
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT default_provider, default_model, deepseek_api_key, deepseek_base_url
            FROM user_settings
            WHERE deepseek_api_key IS NOT NULL AND TRIM(deepseek_api_key) <> ''
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        raise RuntimeError("No DeepSeek provider seed found in user_settings")
    return {
        "default_provider": str(row["default_provider"] or DEFAULT_PROVIDER),
        "default_model": str(row["default_model"] or DEFAULT_MODEL),
        "deepseek_api_key": str(row["deepseek_api_key"]),
        "deepseek_base_url": str(row["deepseek_base_url"]) if row["deepseek_base_url"] else None,
    }


def _seed_user_provider_and_rebind_world(
    database_path: Path,
    *,
    user_id: str,
    world_id: str,
    seed: dict[str, str | None],
) -> None:
    """把 provider 配置借给临时用户，并把目标 world/lorebook 绑定到该用户。"""
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            """
            UPDATE user_settings
            SET default_provider = ?,
                default_model = ?,
                deepseek_api_key = ?,
                deepseek_base_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                seed["default_provider"],
                seed["default_model"],
                seed["deepseek_api_key"],
                seed["deepseek_base_url"],
                user_id,
            ),
        )
        conn.execute("UPDATE worlds SET owner_user_id = ? WHERE id = ?", (user_id, world_id))
        conn.execute("UPDATE lorebook_entries SET owner_user_id = ? WHERE world_id = ?", (user_id, world_id))
        conn.commit()


def _resolve_world(database_path: Path, *, world_id: Optional[str], world_name: str) -> dict[str, Any]:
    """定位最新的目标世界。"""
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        if world_id:
            row = conn.execute(
                "SELECT id, name, owner_user_id, updated_at, payload FROM worlds WHERE id = ?",
                (world_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, name, owner_user_id, updated_at, payload
                FROM worlds
                WHERE name = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (world_name,),
            ).fetchone()
    if row is None:
        target = world_id or world_name
        raise RuntimeError(f"Target world not found: {target}")
    payload = json.loads(str(row["payload"] or "{}"))
    return {
        "world_id": str(row["id"]),
        "name": str(payload.get("name") or row["name"]),
        "owner_user_id": row["owner_user_id"],
        "updated_at": row["updated_at"],
        "payload": payload,
    }


def _select_lorebook_entries(database_path: Path, world_id: str, limit: int = 5) -> list[dict[str, str]]:
    """优先按预设名称选条目，不足时按顺序补齐。"""
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, type FROM lorebook_entries WHERE world_id = ? ORDER BY rowid ASC",
            (world_id,),
        ).fetchall()

    preferred_map = {str(row["name"]): row for row in rows}
    selected: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for name in PREFERRED_ENTRY_NAMES:
        row = preferred_map.get(name)
        if row is None:
            continue
        entry_id = str(row["id"])
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        selected.append(
            {
                "id": entry_id,
                "name": str(row["name"]),
                "type": str(row["type"] or "unknown"),
            }
        )

    for row in rows:
        if len(selected) >= limit:
            break
        entry_id = str(row["id"])
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        selected.append(
            {
                "id": entry_id,
                "name": str(row["name"]),
                "type": str(row["type"] or "unknown"),
            }
        )

    return selected[:limit]


def _collect_persistence_stats(database_path: Path, *, session_id: str, user_id: str, story_id: str) -> dict[str, Any]:
    """直接查 SQLite，验证消息、事件与故事段落持久化。"""
    with sqlite3.connect(database_path) as conn:
        story_row = conn.execute(
            "SELECT payload FROM stories WHERE id = ? AND owner_user_id = ?",
            (story_id, user_id),
        ).fetchone()
        message_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM story_session_messages
            WHERE session_id = ? AND owner_user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()[0]
        journal_count = conn.execute(
            "SELECT COUNT(*) FROM memory_update_journal WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]

    story_payload = json.loads(str(story_row[0] if story_row else "{}"))
    return {
        "final_story_segments": len(story_payload.get("segments") or []),
        "db_message_count": int(message_count),
        "db_memory_update_count": int(journal_count),
    }


def _count_lorebook_entries(database_path: Path, world_id: str) -> int:
    """统计目标 world 的 Lorebook 条目总数。"""
    with sqlite3.connect(database_path) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM lorebook_entries WHERE world_id = ?",
                (world_id,),
            ).fetchone()[0]
        )


def _create_runtime_copy(service_root: Path, source_db: Path, port: int) -> RuntimeContext:
    """创建运行时副本目录与数据库副本。"""
    run_id = uuid.uuid4().hex[:8]
    runtime_dir = service_root / "data" / f"tes_validation_runtime_{run_id}"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    database_path = runtime_dir / "chatbox.db"
    shutil.copy2(source_db, database_path)
    (runtime_dir / "FileUpload").mkdir(parents=True, exist_ok=True)
    return RuntimeContext(
        runtime_dir=runtime_dir,
        database_path=database_path,
        port=port,
        base_url=f"http://127.0.0.1:{port}",
        server_log_path=runtime_dir / "server.log",
    )


def _cleanup_runtime_dir(runtime_dir: Path) -> None:
    """尽量清理运行时副本目录，规避 Windows 短暂文件锁。"""
    for _ in range(5):
        if not runtime_dir.exists():
            return
        try:
            shutil.rmtree(runtime_dir)
            return
        except PermissionError:
            time.sleep(1)
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir, ignore_errors=True)


def _request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    label: str,
    timeout: float,
    retries: int = 0,
    **kwargs: Any,
) -> Any:
    """对本地 API 调用做短重试，并返回 JSON 结果。"""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.request(method, url, timeout=timeout, **kwargs)
            return _require_ok(response, label)
        except httpx.ReadTimeout as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(1)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{label} failed without response")


def _build_findings(report: dict[str, Any]) -> list[str]:
    """基于结构化结果生成简洁结论。"""
    findings: list[str] = []
    rounds = list(report.get("rounds", []))
    persistence = report.get("persistence", {})
    world = report.get("world", {})

    if rounds and all(int(item.get("contexts_count", 0)) > 0 for item in rounds):
        findings.append("所有生成轮次都命中了世界上下文，Lorebook 注入链路可用。")
    else:
        findings.append("存在未命中上下文的轮次，RAG / 显式设定注入不稳定。")

    if rounds and all(str(item.get("token_source") or "") == "provider_usage" for item in rounds):
        findings.append("所有轮次都拿到了 provider_usage token 统计，外部模型调用链路稳定。")
    else:
        findings.append("部分轮次未拿到 provider_usage token 统计，需检查 provider usage 回传。")

    expected_segments = len(rounds)
    if int(persistence.get("final_story_segments", 0)) == expected_segments:
        findings.append("每轮生成后的故事段落都成功追加并持久化。")
    else:
        findings.append("故事段落数与轮次不一致，段落追加或持久化存在异常。")

    if int(persistence.get("db_message_count", 0)) >= expected_segments * 2:
        findings.append("会话消息已按 user/assistant 双消息模式写入数据库。")
    else:
        findings.append("会话消息落库数量偏少，消息持久化链路需要复核。")

    selected_names = list(world.get("selected_entry_names", []))
    if selected_names:
        findings.append(f"本次优先绑定的设定条目为：{'、'.join(selected_names)}。")

    return findings


def _run_validation(args: argparse.Namespace, runtime: RuntimeContext, report: dict[str, Any]) -> dict[str, Any]:
    """执行主验证流程。"""
    round_limit = min(max(args.round_limit, 1), MAX_ROUNDS)
    seed = _load_provider_seed(runtime.database_path)
    world = _resolve_world(
        runtime.database_path,
        world_id=args.world_id,
        world_name=args.world_name,
    )
    entries = _select_lorebook_entries(runtime.database_path, world["world_id"])

    checks = report["checks"]
    rounds = report["rounds"]
    report["world"] = {
        "world_id": world["world_id"],
        "name": world["name"],
        "source_owner_user_id": world["owner_user_id"],
        "selected_entry_ids": [item["id"] for item in entries],
        "selected_entry_names": [item["name"] for item in entries],
        "lorebook_count": _count_lorebook_entries(runtime.database_path, world["world_id"]),
    }

    suffix = uuid.uuid4().hex[:8]
    login_identifier = f"tes_eval_{suffix}"
    password = f"TesEval_{suffix}!"
    display_name = f"TES Eval {suffix}"

    with httpx.Client(base_url=runtime.base_url, timeout=30.0) as client:
        health = _request_json(client, "GET", "/api/v2/health", label="health", timeout=10.0, retries=1)
        checks.append({"name": "health", "status": "PASS", "detail": json.dumps(health, ensure_ascii=False)})

        register = _request_json(
            client,
            "POST",
            "/api/v2/auth/register",
            label="auth/register",
            timeout=20.0,
            retries=1,
            json={
                "login_identifier": login_identifier,
                "password": password,
                "display_name": display_name,
            },
        )
        user_id = str(register["user"]["user_id"])
        _seed_user_provider_and_rebind_world(
            runtime.database_path,
            user_id=user_id,
            world_id=world["world_id"],
            seed=seed,
        )
        checks.append({"name": "auth_register", "status": "PASS", "detail": f"user_id={user_id}"})

        me = _request_json(client, "GET", "/api/v2/auth/me", label="auth/me", timeout=20.0, retries=1)
        checks.append({"name": "auth_me", "status": "PASS", "detail": f"user_id={me['user_id']}"})

        world_body = _request_json(
            client,
            "GET",
            f"/api/v2/worlds/{world['world_id']}",
            label="get_world",
            timeout=20.0,
            retries=1,
        )
        checks.append({"name": "world_access", "status": "PASS", "detail": f"world={world_body.get('name')}"})

        provider_check = _request_json(
            client,
            "POST",
            "/api/v2/providers/test-connection",
            label="providers/test-connection",
            timeout=60.0,
            json={"provider": DEFAULT_PROVIDER},
        )
        if not provider_check.get("success"):
            raise RuntimeError(f"Provider connectivity failed: {json.dumps(provider_check, ensure_ascii=False)}")
        checks.append(
            {
                "name": "provider_connectivity",
                "status": "PASS",
                "detail": f"latency_ms={provider_check.get('latency_ms')}",
            }
        )

        story = _request_json(
            client,
            "POST",
            "/api/v2/stories",
            label="create_story",
            timeout=30.0,
            retries=1,
            json={
                "world_id": world["world_id"],
                "title": f"TES Validation {suffix}",
                "metadata": {"validation_run": True},
            },
        )
        session = _request_json(
            client,
            "POST",
            "/api/v2/story/session",
            label="create_session",
            timeout=30.0,
            retries=1,
            json={"world_id": world["world_id"]},
        )
        checks.append({"name": "story_and_session_create", "status": "PASS", "detail": f"story_id={story['id']}"})

        for idx, prompt in enumerate(ROUND_PROMPTS[:round_limit], start=1):
            generated = _request_json(
                client,
                "POST",
                "/api/v2/story/generate",
                label=f"story/generate round {idx}",
                timeout=args.request_timeout,
                json={
                    "session_id": session["session_id"],
                    "story_id": story["id"],
                    "world_id": world["world_id"],
                    "user_input": prompt,
                    "provider": seed["default_provider"] or DEFAULT_PROVIDER,
                    "model": seed["default_model"] or DEFAULT_MODEL,
                    "use_rag": True,
                    "top_k": 5,
                    "selected_context_entry_ids": [item["id"] for item in entries],
                    "language": "zh-CN",
                    "mode": "narrative",
                    "creation_mode": "improv",
                    "progress_intent": "hold",
                    "temperature": 0.8,
                    "max_tokens": 420,
                },
            )
            appended = _request_json(
                client,
                "POST",
                f"/api/v2/stories/{story['id']}/segments",
                label=f"append story segment round {idx}",
                timeout=30.0,
                retries=1,
                json={
                    "prompt": prompt,
                    "creation_mode": generated.get("creation_mode") or "improv",
                    "content": generated.get("output_text") or "",
                    "retrieved_context": [
                        f"{item.get('name', '')} · {item.get('type', '')}".strip(" ·")
                        for item in list(generated.get("contexts") or [])
                    ],
                    "runtime_state_snapshot": generated.get("runtime_state_snapshot") or None,
                },
            )

            rounds.append(
                {
                    "round": idx,
                    "prompt": prompt,
                    "output_chars": len(generated.get("output_text") or ""),
                    "contexts_count": len(generated.get("contexts") or []),
                    "context_names": [item.get("name") for item in list(generated.get("contexts") or [])],
                    "activation_sources": [
                        item.get("source") or item.get("event")
                        for item in list(generated.get("activation_logs") or [])
                    ],
                    "memory_updates_count": len(generated.get("memory_updates") or []),
                    "token_source": generated.get("token_source"),
                    "tokens_used": generated.get("tokens_used"),
                    "generation_time": generated.get("generation_time"),
                    "output_preview": (generated.get("output_text") or "")[:280],
                    "story_segments_after_append": len(appended.get("segments") or []),
                }
            )

        story_memory = _request_json(
            client,
            "GET",
            f"/api/v2/story/session/{session['session_id']}/story-memory",
            label="story-memory",
            timeout=30.0,
            retries=1,
        )
        final_story = _request_json(
            client,
            "GET",
            f"/api/v2/stories/{story['id']}",
            label="get_story",
            timeout=30.0,
            retries=1,
        )
        persistence = _collect_persistence_stats(
            runtime.database_path,
            session_id=session["session_id"],
            user_id=user_id,
            story_id=story["id"],
        )
        persistence["story_memory_timeline_total"] = story_memory.get("timeline_total")

    report = {
        "summary": {
            "overall_status": "PASS",
            "executed_at": _utc_like_timestamp(),
            "base_url": runtime.base_url,
            "round_count": len(rounds),
            "runtime_dir": str(runtime.runtime_dir),
        },
        "checks": checks,
        "world": report["world"],
        "rounds": rounds,
        "persistence": {
            **persistence,
            "story_id": story["id"],
            "session_id": session["session_id"],
            "final_story_segments_api": len(final_story.get("segments") or []),
            "user_id": user_id,
        },
        "findings": [],
        "errors": [],
    }
    report["findings"] = _build_findings(report)
    return report


def run(args: argparse.Namespace, paths: ReportPaths) -> dict[str, Any]:
    """执行完整流程并返回结构化报告。"""
    service_root = Path(__file__).resolve().parents[1]
    source_db = Path(args.database_path).resolve()
    runtime = _create_runtime_copy(service_root, source_db, args.port)
    process: Optional[subprocess.Popen[str]] = None
    keep_runtime = bool(args.keep_runtime_dir)

    report: dict[str, Any] = {
        "summary": {
            "overall_status": "RUNNING",
            "executed_at": _utc_like_timestamp(),
            "base_url": runtime.base_url,
            "round_count": 0,
            "runtime_dir": str(runtime.runtime_dir),
            "server_log_path": str(runtime.server_log_path),
        },
        "checks": [],
        "world": {"world_id": args.world_id, "name": args.world_name},
        "rounds": [],
        "persistence": {},
        "findings": [],
        "errors": [],
    }

    try:
        process = _start_server(service_root, runtime)
        _wait_for_server(runtime.base_url, args.server_timeout_seconds)
        report = _run_validation(args, runtime, report)
    except Exception as exc:
        keep_runtime = True
        report["summary"]["overall_status"] = "FAIL"
        report["summary"]["executed_at"] = _utc_like_timestamp()
        report["summary"]["round_count"] = len(report["rounds"])
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        _stop_server(process)
        if report["summary"].get("overall_status") == "PASS":
            report["summary"]["round_count"] = len(report["rounds"])
        _write_report(report, paths)
        if runtime.runtime_dir.exists() and not keep_runtime:
            _cleanup_runtime_dir(runtime.runtime_dir)

    return report


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    service_root = Path(__file__).resolve().parents[1]
    date_tag = _utc_like_timestamp()
    report_dir = service_root / "docs" / "TestResult"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-path",
        default=str(service_root / "data" / "chatbox.db"),
    )
    parser.add_argument("--world-id", default=None)
    parser.add_argument("--world-name", default=DEFAULT_WORLD_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--round-limit", type=int, default=4)
    parser.add_argument("--request-timeout", type=float, default=240.0)
    parser.add_argument("--server-timeout-seconds", type=int, default=90)
    parser.add_argument("--keep-runtime-dir", action="store_true")
    parser.add_argument(
        "--report-json",
        default=str(report_dir / f"TESWorld_Validation_Run_{date_tag}.json"),
    )
    parser.add_argument(
        "--report-md",
        default=str(report_dir / f"TESWorld_Validation_Report_{date_tag}.md"),
    )
    return parser.parse_args()


def main() -> int:
    """运行验证并打印报告摘要。"""
    args = parse_args()
    if args.round_limit > MAX_ROUNDS:
        print(
            json.dumps(
                {"success": False, "error": f"round_limit must be <= {MAX_ROUNDS}"},
                ensure_ascii=False,
            )
        )
        return 1

    paths = ReportPaths(
        json_path=Path(args.report_json).resolve(),
        md_path=Path(args.report_md).resolve(),
    )
    report = run(args, paths)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON report: {paths.json_path}")
    print(f"MD report: {paths.md_path}")
    return 0 if report["summary"].get("overall_status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
