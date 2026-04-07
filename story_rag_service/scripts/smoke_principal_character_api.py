"""关键角色故事生成 API 契约冒烟测试。

该脚本通过补丁替换图执行入口，以便在不启动完整运行栈的情况下
验证 API schema 与路由接线。
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app
from api.v2.story import generation_routes


async def _fake_run_story_graph(state):
    payload = state["request_payload"]
    return {
        "v2_response": {
            "session_id": payload["session_id"],
            "thread_id": payload.get("thread_id") or payload["session_id"],
            "output_text": "测试通过：关键角色交流字段已接入。",
            "contexts": [
                {
                    "name": "沈砚",
                    "type": "character",
                    "content": "关键角色上下文已显式注入。",
                    "score": 1.0,
                }
            ],
            "activation_logs": [
                {
                    "source": "dialogue_control",
                    "event": "applied",
                    "principal_character_id": payload.get("principal_character_id"),
                    "dialogue_mode": payload.get("dialogue_mode"),
                    "force_dialogue_round": payload.get("force_dialogue_round"),
                }
            ],
            "story_state_snapshot": None,
            "summary_memory_snapshot": None,
            "model": payload.get("model") or "smoke-model",
            "generation_time": 0.01,
            "choices": [],
            "tokens_used": {"input_tokens": 12, "output_tokens": 18, "total_tokens": 30},
            "token_source": "estimated",
        }
    }


def main() -> None:
    original = generation_routes.run_story_graph
    generation_routes.run_story_graph = _fake_run_story_graph

    try:
        client = TestClient(app)
        payload = {
            "session_id": "smoke-session-001",
            "user_input": "让沈砚在密室里开口，说出那句藏着威胁的话。",
            "world_id": "world-smoke",
            "persona_id": "persona-smoke",
            "principal_character_id": "entry-shenyan",
            "dialogue_mode": "required",
            "dialogue_target": "主角",
            "dialogue_intent": "施压并抛出线索",
            "dialogue_style_hint": "简短、冷淡、带试探意味",
            "force_dialogue_round": True,
            "selected_context_entry_ids": ["entry-shenyan"],
            "model": "smoke-model",
        }

        response = client.post("/api/v2/story/generate", json=payload)
        response.raise_for_status()
        body = response.json()

        assert body["session_id"] == payload["session_id"]
        assert body["output_text"]
        assert body["activation_logs"][0]["principal_character_id"] == payload["principal_character_id"]
        assert body["activation_logs"][0]["dialogue_mode"] == payload["dialogue_mode"]
        print("[OK] principal character API smoke passed")
    finally:
        generation_routes.run_story_graph = original


if __name__ == "__main__":
    main()