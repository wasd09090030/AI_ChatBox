"""
P0 冒烟测试：会话管理 + SSE 流式持久化。

用法：
    python scripts/smoke_persistence_streaming.py

可选环境变量：
    SMOKE_BASE_URL=http://127.0.0.1:8000
    RUN_LLM_SMOKE=true   （默认：true）
"""

from __future__ import annotations

import json
import os
import uuid

import httpx

# 统一服务地址，允许通过环境变量切换到远端或本地实例。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# 控制是否执行依赖模型推理的流式冒烟测试。
RUN_LLM_SMOKE = os.getenv("RUN_LLM_SMOKE", "true").lower() == "true"
# 为 HTTP 请求设置统一超时时间，避免脚本无限阻塞。
TIMEOUT = 60.0


def _assert(cond: bool, msg: str) -> None:
    """统一断言输出格式，失败时附带可读的 smoke 错误上下文。"""
    if not cond:
        raise AssertionError(f"[FAIL] {msg}")


def test_session_create_and_get(client: httpx.Client) -> str:
    """POST /story/session → GET /story/session/{id}，返回 session_id。"""
    session_payload = {
        "world_id": None,
        "character_card_id": None,
        "persona_id": None,
    }
    r = client.post(f"{BASE_URL}/api/v2/story/session", json=session_payload)
    _assert(r.status_code == 200, f"POST /story/session status={r.status_code} body={r.text[:200]}")
    data = r.json()
    _assert("session_id" in data, f"session_id missing in response: {data}")
    session_id = data["session_id"]
    print(f"[OK] POST /api/v2/story/session → session_id={session_id}")

    r2 = client.get(f"{BASE_URL}/api/v2/story/session/{session_id}")
    _assert(r2.status_code == 200, f"GET /story/session/{session_id} status={r2.status_code} body={r2.text[:200]}")
    info = r2.json()
    _assert(info["session_id"] == session_id, f"Returned session_id mismatch: {info}")
    print(f"[OK] GET /api/v2/story/session/{session_id}")
    return session_id


def test_session_not_found(client: httpx.Client) -> None:
    """读取不存在会话应返回 404。"""
    r = client.get(f"{BASE_URL}/api/v2/story/session/NOT_EXIST_{uuid.uuid4().hex}")
    _assert(r.status_code == 404, f"Expected 404 for unknown session, got {r.status_code}")
    print("[OK] GET non-existent session returns 404")


def test_streaming_endpoint(client: httpx.Client, session_id: str) -> None:
    """POST /story/generate/stream → SSE 分片 → 最终 done 事件。"""
    payload = {
        "session_id": session_id,
        "user_input": "一只猫走进了魔法森林。",
        "use_rag": False,
        "temperature": 0.7,
        "max_tokens": 200,
        "mode": "narrative",
    }
    chunks_received = 0
    final_event = None

    with client.stream("POST", f"{BASE_URL}/api/v2/story/generate/stream", json=payload) as resp:
        _assert(resp.status_code == 200, f"Stream endpoint status={resp.status_code}")
        content_type = resp.headers.get("content-type", "")
        _assert("text/event-stream" in content_type, f"Expected text/event-stream, got {content_type}")

        buffer = ""
        for text in resp.iter_text():
            if not text:
                continue
            buffer += text
            lines = buffer.split("\n")
            buffer = lines.pop() or ""
            for line in lines:
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                raw = line[len("data: "):]
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if event.get("done") is False:
                    chunks_received += 1
                elif event.get("done") is True:
                    final_event = event
                    break

            if final_event is not None:
                break

    _assert(chunks_received > 0, "No chunk events received from stream")
    _assert(final_event is not None, "No final 'done' event received from stream")
    _assert("session_id" in final_event, f"Final event missing session_id: {final_event}")
    generated_text = str(final_event.get("generated_text") or final_event.get("output_text") or "")
    _assert(bool(generated_text.strip()), f"Final done event missing generated_text/output_text: {final_event}")
    print(f"[OK] POST /api/v2/story/generate/stream → {chunks_received} chunks + done event ({len(generated_text)} chars)")


def test_delete_last_message(client: httpx.Client, session_id: str) -> None:
    """DELETE /story/session/{id}/messages/last → deleted=true。"""
    r = client.delete(f"{BASE_URL}/api/v2/story/session/{session_id}/messages/last")
    _assert(
        r.status_code == 200,
        f"DELETE last message status={r.status_code} body={r.text[:200]}",
    )
    data = r.json()
    _assert(data.get("deleted") is True, f"Expected deleted=true, got: {data}")
    print(f"[OK] DELETE /api/v2/story/session/{session_id}/messages/last")


def test_delete_last_message_empty_session(client: httpx.Client) -> None:
    """空会话执行 DELETE 应返回 404。"""
    # 创建一个没有消息的新会话。
    r = client.post(f"{BASE_URL}/api/v2/story/session", json={})
    _assert(r.status_code == 200, "Could not create empty session")
    sid = r.json()["session_id"]

    r2 = client.delete(f"{BASE_URL}/api/v2/story/session/{sid}/messages/last")
    _assert(r2.status_code == 404, f"Expected 404 for empty session, got {r2.status_code}: {r2.text[:200]}")
    print("[OK] DELETE last message on empty session returns 404")


def main() -> None:
    """执行会话管理、SSE 持久化与删除回滚等 P0 关键链路检查。"""
    print(f"[SMOKE-P0] base_url={BASE_URL}  llm={RUN_LLM_SMOKE}")

    with httpx.Client(timeout=TIMEOUT) as client:
        # 基础健康检查。
        r = client.get(f"{BASE_URL}/api/v2/health")
        _assert(r.status_code == 200, f"Health check failed: {r.status_code}")
        print("[OK] /api/v2/health")

        # 会话管理。
        session_id = test_session_create_and_get(client)
        test_session_not_found(client)

        if RUN_LLM_SMOKE:
            # SSE 流式生成。
            test_streaming_endpoint(client, session_id)

            # 回滚：删除刚才流式生成产生的最后一条消息。
            test_delete_last_message(client, session_id)
        else:
            print("[SKIP] LLM smoke tests (set RUN_LLM_SMOKE=true)")

        # 边界场景：空会话删除最后消息。
        test_delete_last_message_empty_session(client)

    print("\n[DONE] All P0 persistence+streaming smoke checks passed ✓")


if __name__ == "__main__":
    main()
