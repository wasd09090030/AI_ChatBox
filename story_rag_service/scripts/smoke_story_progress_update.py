"""显式故事进度更新冒烟测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# 将仓库根目录加入导入路径，确保脚本可直接以 `python scripts/...` 方式运行。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service_context import init_services, reset_container
from main import app


def main() -> None:
    """验证故事进度字段的绑定、清空与解绑语义是否符合约定。"""
    reset_container()
    init_services()
    client = TestClient(app)

    world = client.post(
        "/api/v2/worlds",
        json={
            "name": "Smoke Phase3 世界",
            "description": "验证显式剧本推进更新",
            "genre": "fantasy",
        },
    ).json()

    try:
        script_design = client.post(
            "/api/v2/script-designs",
            json={
                "world_id": world["id"],
                "title": "双阶段推进验证",
                "status": "active",
                "stage_outlines": [
                    {"id": "stage-1", "title": "开端", "order": 0, "goal": "建立局势"},
                    {"id": "stage-2", "title": "余波", "order": 1, "goal": "进入无事件阶段"},
                ],
                "event_nodes": [
                    {
                        "id": "event-1",
                        "stage_id": "stage-1",
                        "title": "遭遇前哨",
                        "order": 0,
                        "status": "pending",
                        "event_type": "setup",
                        "objective": "让主角接触第一波冲突",
                    }
                ],
            },
        )
        script_design.raise_for_status()
        design_body = script_design.json()

        story_response = client.post(
            "/api/v2/stories",
            json={
                "world_id": world["id"],
                "title": "Smoke Phase3 故事",
            },
        )
        story_response.raise_for_status()
        story = story_response.json()

        update_response = client.put(
            f"/api/v2/stories/{story['id']}/progress",
            json={
                "script_design_id": design_body["id"],
                "active_stage_id": "stage-1",
                "active_event_id": "event-1",
                "follow_script_design": True,
            },
        )
        update_response.raise_for_status()
        updated_story = update_response.json()
        assert updated_story["metadata"]["script_design_id"] == design_body["id"]
        assert updated_story["metadata"]["active_stage_id"] == "stage-1"
        assert updated_story["metadata"]["active_event_id"] == "event-1"
        assert updated_story["metadata"]["follow_script_design"] is True

        clear_event_response = client.put(
            f"/api/v2/stories/{story['id']}/progress",
            json={
                "active_stage_id": "stage-2",
                "active_event_id": None,
            },
        )
        clear_event_response.raise_for_status()
        cleared_story = clear_event_response.json()
        assert cleared_story["metadata"]["script_design_id"] == design_body["id"]
        assert cleared_story["metadata"]["active_stage_id"] == "stage-2"
        assert "active_event_id" not in cleared_story["metadata"], cleared_story["metadata"]

        unbind_response = client.put(
            f"/api/v2/stories/{story['id']}/progress",
            json={
                "script_design_id": None,
                "active_stage_id": None,
                "follow_script_design": False,
            },
        )
        unbind_response.raise_for_status()
        unbound_story = unbind_response.json()
        assert "script_design_id" not in unbound_story["metadata"], unbound_story["metadata"]
        assert "active_stage_id" not in unbound_story["metadata"], unbound_story["metadata"]
        assert unbound_story["metadata"]["follow_script_design"] is False
    finally:
        cleanup_world_response = client.delete(f"/api/v2/worlds/{world['id']}")
        cleanup_world_response.raise_for_status()

    print("[OK] story progress explicit update smoke passed")


if __name__ == "__main__":
    main()