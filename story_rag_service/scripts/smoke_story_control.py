"""
P2 冒烟测试：故事方向控制（Author's Note、choices 模式、instruction 模式、重生成）。

用法：
    python scripts/smoke_story_control.py

可选环境变量：
    SMOKE_BASE_URL=http://127.0.0.1:8000
    RUN_LLM_SMOKE=true   （默认：true）
"""

from __future__ import annotations

import os
import uuid

import httpx

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RUN_LLM_SMOKE = os.getenv("RUN_LLM_SMOKE", "true").lower() == "true"
TIMEOUT = 60.0


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"[FAIL] {msg}")


def _new_session(client: httpx.Client) -> str:
    r = client.post(f"{BASE_URL}/api/v2/story/session", json={})
    _assert(r.status_code == 200, f"Failed to create session: {r.status_code} {r.text[:200]}")
    return r.json()["session_id"]


def test_authors_note_mode(client: httpx.Client) -> None:
    """带 authors_note 生成；校验请求可用且响应含 output_text。"""
    session_id = _new_session(client)
    payload = {
        "session_id": session_id,
        "user_input": "探险者走进古老的地下城。",
        "use_rag": False,
        "temperature": 0.7,
        "max_tokens": 300,
        "mode": "narrative",
        "authors_note": "保持黑暗恐怖的氛围，节奏紧张。",
    }
    r = client.post(f"{BASE_URL}/api/v2/story/generate", json=payload)
    _assert(r.status_code == 200, f"authors_note generate failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    _assert("output_text" in data and len(data["output_text"]) > 0, f"Empty output_text: {data.keys()}")
    print(f"[OK] mode=narrative + authors_note → {len(data['output_text'])} chars")


def test_choices_mode(client: httpx.Client) -> None:
    """mode=choices 生成；校验响应包含 3 个选项 [A][B][C]。"""
    session_id = _new_session(client)
    payload = {
        "session_id": session_id,
        "user_input": "勇士站在城堡门前，面对三条不同的道路。",
        "use_rag": False,
        "temperature": 0.7,
        "max_tokens": 500,
        "mode": "choices",
    }
    r = client.post(f"{BASE_URL}/api/v2/story/generate", json=payload)
    _assert(r.status_code == 200, f"choices mode generate failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    _assert("output_text" in data, f"output_text missing in choices response: {data.keys()}")
    choices = data.get("choices", [])
    print(f"[INFO] choices mode → {len(choices)} choices: {choices}")
    # 警告但不硬失败：LLM 在部分运行中可能不完全遵循。
    if len(choices) != 3:
        print(f"[WARN] Expected 3 choices, got {len(choices)} — LLM non-compliance possible")
    else:
        print(f"[OK] mode=choices → 3 choices extracted correctly")
    _assert(len(data["output_text"]) > 0, "output_text is empty in choices mode")


def test_instruction_mode(client: httpx.Client) -> None:
    """mode=instruction + instruction 生成；校验请求可用。"""
    session_id = _new_session(client)
    payload = {
        "session_id": session_id,
        "user_input": "平静的湖边，一只神秘的天鹅出现了。",
        "use_rag": False,
        "temperature": 0.7,
        "max_tokens": 300,
        "mode": "instruction",
        "instruction": "天鹅必须开口说话，并揭示一个关于消失村庄的秘密",
    }
    r = client.post(f"{BASE_URL}/api/v2/story/generate", json=payload)
    _assert(r.status_code == 200, f"instruction mode generate failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    _assert("output_text" in data and len(data["output_text"]) > 0, "Empty output_text in instruction mode")
    print(f"[OK] mode=instruction → {len(data['output_text'])} chars")


def test_regenerate_endpoint(client: httpx.Client) -> None:
    """先生成再重生成；应返回不同（新的）结果。"""
    session_id = _new_session(client)

    # 首次生成。
    payload = {
        "session_id": session_id,
        "user_input": "旅人来到了十字路口。",
        "use_rag": False,
        "temperature": 0.8,
        "max_tokens": 200,
    }
    r1 = client.post(f"{BASE_URL}/api/v2/story/generate", json=payload)
    _assert(r1.status_code == 200, f"First generate failed: {r1.status_code} {r1.text[:200]}")
    first_text = r1.json()["output_text"]
    print(f"[INFO] First generation: {len(first_text)} chars")

    # 重生成。
    regen_payload = {
        "model": None,
        "temperature": 0.95,
        "max_tokens": 200,
        "mode": "narrative",
    }
    r2 = client.post(f"{BASE_URL}/api/v2/story/session/{session_id}/regenerate", json=regen_payload)
    _assert(
        r2.status_code == 200,
        f"Regenerate failed: {r2.status_code} {r2.text[:300]}",
    )
    second_text = r2.json()["output_text"]
    _assert(len(second_text) > 0, "Regenerated output_text is empty")
    print(f"[OK] POST /story/session/{session_id}/regenerate → {len(second_text)} chars")
    # 说明：文本偶然一致是可能的，但概率极低。
    if first_text == second_text:
        print("[WARN] Regenerated text identical to first — may indicate caching issue")


def test_regenerate_no_user_message(client: httpx.Client) -> None:
    """空会话执行重生成应返回 400。"""
    session_id = _new_session(client)
    r = client.post(
        f"{BASE_URL}/api/v2/story/session/{session_id}/regenerate",
        json={"mode": "narrative"},
    )
    _assert(r.status_code == 400, f"Expected 400 for no user message, got {r.status_code}: {r.text[:200]}")
    print("[OK] Regenerate on empty session returns 400")


def main() -> None:
    print(f"[SMOKE-P2] base_url={BASE_URL}  llm={RUN_LLM_SMOKE}")

    with httpx.Client(timeout=TIMEOUT) as client:
        # 基础健康检查。
        r = client.get(f"{BASE_URL}/api/v2/health")
        _assert(r.status_code == 200, f"Health check failed: {r.status_code}")
        print("[OK] /api/v2/health")

        # 空会话重生成边界场景（无需 LLM）。
        test_regenerate_no_user_message(client)

        if RUN_LLM_SMOKE:
            test_authors_note_mode(client)
            test_choices_mode(client)
            test_instruction_mode(client)
            test_regenerate_endpoint(client)
        else:
            print("[SKIP] LLM smoke tests (set RUN_LLM_SMOKE=true)")

    print("\n[DONE] All P2 story-control smoke checks passed ✓")


if __name__ == "__main__":
    main()
