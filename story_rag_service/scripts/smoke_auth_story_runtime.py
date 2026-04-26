"""登录后故事生成主链路运行级 smoke。

要求：
1. 服务已通过 `.venv` 启动；
2. SQLite 中存在一份可用的 deepseek 用户级配置，用于借给本次 smoke 新用户；
3. 不打印任何密钥，只输出验证摘要。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx


def _require_ok(response: httpx.Response, label: str) -> Any:
    if response.status_code >= 400:
        raise RuntimeError(
            f"{label} failed: HTTP {response.status_code} -> {response.text[:500]}"
        )
    return response.json()


def _wait_for_server(base_url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/", timeout=5.0)
            if response.status_code == 200:
                return
        except Exception as exc:  # pragma: no cover - runtime smoke only
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"Server not ready within {timeout_seconds}s: {last_error}")


def _load_legacy_provider_seed(database_path: Path) -> dict[str, str | None]:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT user_id, default_provider, default_model, deepseek_api_key, deepseek_base_url
            FROM user_settings
            WHERE deepseek_api_key IS NOT NULL AND TRIM(deepseek_api_key) <> ''
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        raise RuntimeError("No legacy deepseek provider config found in user_settings")
    return {
        "legacy_user_id": str(row["user_id"]),
        "default_provider": str(row["default_provider"] or "deepseek"),
        "default_model": str(row["default_model"] or "deepseek-chat"),
        "deepseek_api_key": str(row["deepseek_api_key"]),
        "deepseek_base_url": (
            str(row["deepseek_base_url"]) if row["deepseek_base_url"] else None
        ),
    }


def _seed_user_provider_config(
    database_path: Path,
    *,
    user_id: str,
    seed: dict[str, str | None],
) -> None:
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
        conn.execute(
            "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def _fetch_owner_ids(
    database_path: Path,
    *,
    world_id: str,
    story_id: str,
    session_id: str,
) -> dict[str, Any]:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        world_row = conn.execute(
            "SELECT owner_user_id FROM worlds WHERE id = ?",
            (world_id,),
        ).fetchone()
        story_row = conn.execute(
            "SELECT owner_user_id, payload FROM stories WHERE id = ?",
            (story_id,),
        ).fetchone()
        session_row = conn.execute(
            "SELECT owner_user_id FROM story_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        message_rows = conn.execute(
            "SELECT owner_user_id, role FROM story_session_messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()

    if world_row is None or story_row is None or session_row is None:
        raise RuntimeError("Persistence verification failed: missing world/story/session row")

    story_payload = json.loads(story_row["payload"])
    return {
        "world_owner_user_id": world_row["owner_user_id"],
        "story_owner_user_id": story_row["owner_user_id"],
        "session_owner_user_id": session_row["owner_user_id"],
        "story_segment_count": len(story_payload.get("segments") or []),
        "message_roles": [row["role"] for row in message_rows],
        "message_owner_user_ids": [row["owner_user_id"] for row in message_rows],
    }


def run(base_url: str, database_path: Path, timeout_seconds: int) -> dict[str, Any]:
    _wait_for_server(base_url, timeout_seconds)
    seed = _load_legacy_provider_seed(database_path)

    suffix = uuid.uuid4().hex[:8]
    login_identifier = f"smoke_{suffix}"
    password = f"SmokePass_{suffix}!"
    display_name = f"Smoke {suffix}"
    world_name = f"SmokeWorld-{suffix}"
    story_title = f"SmokeStory-{suffix}"
    session_id = f"smoke-session-{suffix}"

    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        register_body = _require_ok(
            client.post(
                "/api/v2/auth/register",
                json={
                    "login_identifier": login_identifier,
                    "password": password,
                    "display_name": display_name,
                },
            ),
            "register",
        )
        user_id = register_body["user"]["user_id"]
        _seed_user_provider_config(database_path, user_id=user_id, seed=seed)

        _require_ok(client.post("/api/v2/auth/logout"), "logout")
        login_body = _require_ok(
            client.post(
                "/api/v2/auth/login",
                json={
                    "login_identifier": login_identifier,
                    "password": password,
                },
            ),
            "login",
        )
        me_body = _require_ok(client.get("/api/v2/auth/me"), "auth/me")
        if me_body["user_id"] != user_id:
            raise RuntimeError("Authenticated user mismatch after login")

        connection_body = _require_ok(
            client.post(
                "/api/v2/providers/test-connection",
                json={"provider": "deepseek"},
            ),
            "providers/test-connection",
        )
        if not connection_body.get("success"):
            raise RuntimeError(
                f"Provider connection not ready: {json.dumps(connection_body, ensure_ascii=False)}"
            )

        world_body = _require_ok(
            client.post(
                "/api/v2/worlds",
                json={
                    "name": world_name,
                    "description": "运行级 smoke 世界，用于验证登录后故事生成主链路。",
                    "genre": "fantasy",
                    "setting": "边境城邦的雨夜",
                    "rules": "魔法稀缺但真实存在。",
                },
            ),
            "create world",
        )
        story_body = _require_ok(
            client.post(
                "/api/v2/stories",
                json={
                    "world_id": world_body["id"],
                    "title": story_title,
                    "metadata": {},
                },
            ),
            "create story",
        )
        session_body = _require_ok(
            client.post(
                "/api/v2/story/session",
                json={
                    "session_id": session_id,
                    "world_id": world_body["id"],
                },
            ),
            "create session",
        )
        generate_body = _require_ok(
            client.post(
                "/api/v2/story/generate",
                json={
                    "session_id": session_body["session_id"],
                    "story_id": story_body["id"],
                    "world_id": world_body["id"],
                    "user_input": "请用中文写一个 120 字左右的故事开场，主角刚抵达一座风雨中的边境城。",
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "creation_mode": "improv",
                    "progress_intent": "hold",
                    "use_rag": True,
                    "temperature": 0.8,
                    "max_tokens": 512,
                    "language": "zh-CN",
                    "mode": "narrative",
                },
            ),
            "story/generate",
        )
        _require_ok(
            client.post(
                f"/api/v2/stories/{story_body['id']}/segments",
                json={
                    "prompt": "请用中文写一个 120 字左右的故事开场，主角刚抵达一座风雨中的边境城。",
                    "creation_mode": generate_body.get("creation_mode") or "improv",
                    "content": generate_body.get("output_text") or "",
                    "retrieved_context": [
                        f"{item.get('name', '')} · {item.get('type', '')}".strip(" ·")
                        for item in list(generate_body.get("contexts") or [])
                    ],
                    "runtime_state_snapshot": generate_body.get("runtime_state_snapshot") or None,
                },
            ),
            "append story segment",
        )
        story_after_body = _require_ok(
            client.get(f"/api/v2/stories/{story_body['id']}"),
            "get story",
        )
        session_after_body = _require_ok(
            client.get(f"/api/v2/story/session/{session_id}"),
            "get session",
        )

    persistence = _fetch_owner_ids(
        database_path,
        world_id=world_body["id"],
        story_id=story_body["id"],
        session_id=session_id,
    )
    if persistence["story_segment_count"] < 1:
        raise RuntimeError("Story segments were not persisted")
    if "assistant" not in persistence["message_roles"]:
        raise RuntimeError("Assistant message was not persisted into story_session_messages")
    if any(owner_id != user_id for owner_id in persistence["message_owner_user_ids"]):
        raise RuntimeError("story_session_messages owner_user_id mismatch")
    if persistence["world_owner_user_id"] != user_id:
        raise RuntimeError("world owner_user_id mismatch")
    if persistence["story_owner_user_id"] != user_id:
        raise RuntimeError("story owner_user_id mismatch")
    if persistence["session_owner_user_id"] != user_id:
        raise RuntimeError("session owner_user_id mismatch")

    return {
        "user_id": user_id,
        "login_identifier": login_identifier,
        "world_id": world_body["id"],
        "story_id": story_body["id"],
        "session_id": session_id,
        "provider_connection_status": connection_body["status"],
        "generated_text_preview": (generate_body.get("output_text") or "")[:120],
        "story_segments": len(story_after_body.get("segments") or []),
        "session_first_message_sent": session_after_body.get("first_message_sent"),
        "message_roles": persistence["message_roles"],
        "activation_logs_count": len(generate_body.get("activation_logs") or []),
        "memory_updates_count": len(generate_body.get("memory_updates") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument(
        "--database-path",
        default=str(Path(__file__).resolve().parents[1] / "data" / "chatbox.db"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    try:
        result = run(
            base_url=args.base_url.rstrip("/"),
            database_path=Path(args.database_path),
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:  # pragma: no cover - runtime smoke only
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({"success": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
