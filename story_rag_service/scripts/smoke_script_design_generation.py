"""剧本设计第二阶段生成与绑定契约冒烟测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# 变量作用：路径变量 PROJECT_ROOT，用于定位文件系统资源。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app
from api.service_context import init_services, reset_container
from api.v2.story import generation_routes


async def _fake_run_story_graph(state):
    """功能：处理 fake run 故事 graph。"""
    payload = state["request_payload"]
    return {
        "v2_response": {
            "session_id": payload["session_id"],
            "thread_id": payload.get("thread_id") or payload["session_id"],
            "output_text": "测试通过：剧本设计约束字段已接入。",
            "contexts": [],
            "activation_logs": [
                {
                    "source": "script_design",
                    "event": "applied",
                    "script_design_id": payload.get("script_design_id"),
                    "active_stage_id": payload.get("active_stage_id"),
                    "active_event_id": payload.get("active_event_id"),
                    "follow_script_design": payload.get("follow_script_design"),
                }
            ],
            "story_state_snapshot": None,
            "summary_memory_snapshot": None,
            "model": payload.get("model") or "smoke-model",
            "generation_time": 0.01,
            "choices": [],
            "tokens_used": {"input_tokens": 8, "output_tokens": 12, "total_tokens": 20},
            "token_source": "estimated",
        }
    }


def main() -> None:
    """功能：处理 main。"""
    reset_container()
    init_services()
    client = TestClient(app)

    world = client.post(
        "/api/v2/worlds",
        json={
            "name": "Smoke Phase2 世界",
            "description": "验证剧本设计生成接入",
            "genre": "mystery",
        },
    ).json()

    script_design = client.post(
        "/api/v2/script-designs",
        json={
            "world_id": world["id"],
            "title": "港口阴谋",
            "status": "active",
            "stage_outlines": [
                {"id": "stage-1", "title": "第一幕", "order": 0, "goal": "展开谜团"}
            ],
            "event_nodes": [
                {
                    "id": "event-1",
                    "stage_id": "stage-1",
                    "title": "码头线索浮现",
                    "order": 0,
                    "status": "pending",
                    "event_type": "setup",
                    "objective": "让主角获取第一条硬线索",
                }
            ],
        },
    ).json()

    story = client.post(
        "/api/v2/stories",
        json={"world_id": world["id"], "title": "Smoke Phase2 故事"},
    ).json()

    bind_response = client.put(
        f"/api/v2/stories/{story['id']}",
        json={
            "metadata": {
                "script_design_id": script_design["id"],
                "active_stage_id": "stage-1",
                "active_event_id": "event-1",
                "follow_script_design": True,
            }
        },
    )
    bind_response.raise_for_status()

    bindings_response = client.get(f"/api/v2/script-designs/{script_design['id']}/story-bindings")
    bindings_response.raise_for_status()
    bindings = bindings_response.json()
    assert bindings["count"] == 1, bindings
    assert bindings["items"][0]["story_id"] == story["id"]

    original = generation_routes.run_story_graph
    generation_routes.run_story_graph = _fake_run_story_graph

    try:
        generation_response = client.post(
            "/api/v2/story/generate",
            json={
                "session_id": "smoke-script-design-v2",
                "user_input": "按当前剧本推进，让主角先发现码头上的假线索。",
                "world_id": world["id"],
                "script_design_id": script_design["id"],
                "active_stage_id": "stage-1",
                "active_event_id": "event-1",
                "follow_script_design": True,
                "model": "smoke-model",
            },
        )
        generation_response.raise_for_status()
        body = generation_response.json()
        script_log = next(item for item in body["activation_logs"] if item.get("source") == "script_design")
        assert script_log["script_design_id"] == script_design["id"]
        assert script_log["follow_script_design"] is True
    finally:
        generation_routes.run_story_graph = original

    cleanup_world_response = client.delete(f"/api/v2/worlds/{world['id']}")
    cleanup_world_response.raise_for_status()

    print("[OK] script design phase 2 generation smoke passed")


if __name__ == "__main__":
    main()