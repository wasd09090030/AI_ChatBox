"""
Smoke test: verify story SSE stream contract terminates with a usable done payload.

Usage:
  python scripts/smoke_story_stream_contract.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  RUN_LLM_SMOKE=true   (default: true)
  SMOKE_WORLD_ID=<world-id>
"""

from __future__ import annotations

import json
import os

import httpx

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RUN_LLM_SMOKE = os.getenv("RUN_LLM_SMOKE", "true").lower() == "true"
SMOKE_WORLD_ID = os.getenv("SMOKE_WORLD_ID")
TIMEOUT = 90.0


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"[FAIL] {msg}")


def _create_session(client: httpx.Client) -> str:
    payload = {"world_id": SMOKE_WORLD_ID} if SMOKE_WORLD_ID else {}
    response = client.post(f"{BASE_URL}/api/v2/story/session", json=payload)
    _assert(response.status_code == 200, f"Create session failed: {response.status_code} {response.text[:200]}")
    session_id = response.json()["session_id"]
    print(f"[OK] created session={session_id}")
    return session_id


def test_stream_contract(client: httpx.Client) -> None:
    session_id = _create_session(client)
    payload = {
        "session_id": session_id,
        "user_input": "主角在刑场上醒来，先观察四周的守卫与人群。",
        "world_id": SMOKE_WORLD_ID,
        "use_rag": bool(SMOKE_WORLD_ID),
        "temperature": 0.7,
        "max_tokens": 300,
        "mode": "narrative",
    }

    chunks: list[str] = []
    final_event: dict | None = None

    with client.stream("POST", f"{BASE_URL}/api/v2/story/generate/stream", json=payload) as response:
        _assert(response.status_code == 200, f"Stream status={response.status_code}")
        content_type = response.headers.get("content-type", "")
        _assert("text/event-stream" in content_type, f"Unexpected content-type: {content_type}")

        buffer = ""
        for text in response.iter_text():
            if not text:
                continue
            buffer += text
            lines = buffer.split("\n")
            buffer = lines.pop() or ""

            for line in lines:
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event.get("done") is False:
                    chunk_text = str(event.get("chunk") or "")
                    if chunk_text:
                        chunks.append(chunk_text)
                elif event.get("done") is True:
                    final_event = event
                    break

            if final_event is not None:
                break

    _assert(final_event is not None, "No terminal done event received")
    generated_text = str(final_event.get("generated_text") or final_event.get("output_text") or "")
    _assert(bool(generated_text.strip()), f"Done event missing generated_text/output_text: {final_event}")
    if chunks:
        _assert(generated_text.strip().startswith(chunks[0][: min(len(chunks[0]), 10)].strip()[:10]) or len(generated_text) >= len("".join(chunks)), "Done payload text does not look compatible with streamed chunks")

    print(f"[OK] stream emitted {len(chunks)} chunks")
    print(f"[OK] done payload contains final text ({len(generated_text)} chars)")


def main() -> None:
    print(f"[SMOKE-STREAM-CONTRACT] base_url={BASE_URL} llm={RUN_LLM_SMOKE} world_id={SMOKE_WORLD_ID}")
    with httpx.Client(timeout=TIMEOUT) as client:
        health = client.get(f"{BASE_URL}/api/v2/health")
        _assert(health.status_code == 200, f"Health check failed: {health.status_code}")
        print("[OK] /api/v2/health")

        if RUN_LLM_SMOKE:
            test_stream_contract(client)
        else:
            print("[SKIP] LLM smoke tests (set RUN_LLM_SMOKE=true)")

    print("\n[DONE] Story stream contract smoke checks passed ✓")


if __name__ == "__main__":
    main()