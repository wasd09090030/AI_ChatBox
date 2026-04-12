"""剧本设计第一阶段 API 契约冒烟测试。"""

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


def main() -> None:
    """功能：处理 main。"""
    reset_container()
    init_services()
    client = TestClient(app)

    world_response = client.post(
        "/api/v2/worlds",
        json={
            "name": "Smoke 剧本世界",
            "description": "用于验证剧本设计 Phase 1 API 的测试世界",
            "genre": "mystery",
        },
    )
    world_response.raise_for_status()
    world = world_response.json()

    create_response = client.post(
        "/api/v2/script-designs",
        json={
            "world_id": world["id"],
            "title": "雾港主线",
            "summary": "围绕失踪调查展开的长线剧本。",
            "status": "draft",
        },
    )
    create_response.raise_for_status()
    created = create_response.json()
    script_design_id = created["id"]

    update_response = client.put(
        f"/api/v2/script-designs/{script_design_id}",
        json={
            "status": "active",
            "stage_outlines": [
                {
                    "id": "stage-1",
                    "title": "第一幕",
                    "order": 0,
                    "goal": "建立失踪案与主要冲突",
                    "tension": "主角意识到港口警局在隐瞒真相",
                },
                {
                    "id": "stage-2",
                    "title": "第二幕",
                    "order": 1,
                    "goal": "逼近幕后势力",
                    "expected_turning_point": "主角确认失踪者并未死亡",
                },
            ],
            "event_nodes": [
                {
                    "id": "event-1",
                    "stage_id": "stage-1",
                    "title": "港口线索现身",
                    "order": 0,
                    "status": "pending",
                    "event_type": "setup",
                    "objective": "让主角获得第一条明确线索",
                    "foreshadow_ids": ["foreshadow-1"],
                }
            ],
            "foreshadows": [
                {
                    "id": "foreshadow-1",
                    "title": "断裂怀表",
                    "content": "怀表内部刻着被抹去的家徽",
                    "category": "object",
                    "planted_stage_id": "stage-1",
                    "planted_event_id": "event-1",
                    "expected_payoff_stage_id": "stage-2",
                    "status": "planted",
                    "importance": "high",
                }
            ],
        },
    )
    update_response.raise_for_status()
    updated = update_response.json()
    assert updated["status"] == "active"
    assert len(updated["stage_outlines"]) == 2
    assert updated["event_nodes"][0]["foreshadow_ids"] == ["foreshadow-1"]

    detail_response = client.get(f"/api/v2/script-designs/{script_design_id}")
    detail_response.raise_for_status()
    detail = detail_response.json()
    assert detail["title"] == "雾港主线"

    list_response = client.get("/api/v2/script-designs", params={"world_id": world["id"]})
    list_response.raise_for_status()
    items = list_response.json()
    assert any(item["id"] == script_design_id for item in items)

    bindings_response = client.get(f"/api/v2/script-designs/{script_design_id}/story-bindings")
    bindings_response.raise_for_status()
    bindings = bindings_response.json()
    assert bindings["count"] == 0

    invalid_response = client.put(
        f"/api/v2/script-designs/{script_design_id}",
        json={
            "event_nodes": [
                {
                    "id": "bad-event",
                    "stage_id": "missing-stage",
                    "title": "非法事件",
                    "order": 0,
                }
            ]
        },
    )
    assert invalid_response.status_code == 400, invalid_response.text

    delete_response = client.delete(f"/api/v2/script-designs/{script_design_id}")
    delete_response.raise_for_status()

    cleanup_world_response = client.delete(f"/api/v2/worlds/{world['id']}")
    cleanup_world_response.raise_for_status()

    print("[OK] script design phase 1 API smoke passed")


if __name__ == "__main__":
    main()