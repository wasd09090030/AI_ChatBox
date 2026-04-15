"""
Summary memory smoke test.

Usage:
  python scripts/smoke_summary_memory.py
"""

from __future__ import annotations

import uuid

from services.summary_memory_manager import SummaryMemoryManager


def main() -> None:
    """验证摘要记忆的更新阈值、合并策略与读取一致性。"""
    manager = SummaryMemoryManager()
    session_id = f"summary_smoke_{uuid.uuid4().hex[:8]}"
    world_id = "global"

    assert manager.get_summary(session_id) is None, "new session should have no summary"

    should_update = manager.should_update(session_id, current_turn=4)
    assert should_update is True, "new session should update on threshold"

    first = manager.upsert_summary(
        session_id=session_id,
        world_id=world_id,
        new_summary_text="会话近期推进：玩家调查旧钟楼并发现异常脚印。",
        new_key_facts=["旧钟楼", "异常脚印"],
        last_turn=4,
    )
    assert first["last_turn"] == 4
    assert "旧钟楼" in first["summary_text"]

    should_update_again = manager.should_update(session_id, current_turn=6)
    assert should_update_again is False, "should not update before interval"

    second = manager.upsert_summary(
        session_id=session_id,
        world_id=world_id,
        new_summary_text="会话近期推进：新的线索指向港口仓库。",
        new_key_facts=["港口仓库", "异常脚印"],
        last_turn=8,
    )
    assert second["last_turn"] == 8
    assert "港口仓库" in second["summary_text"]
    assert len(second["key_facts"]) >= 3, "facts should merge without duplication"

    loaded = manager.get_summary(session_id)
    assert loaded is not None
    assert loaded["last_turn"] == 8

    print("[DONE] summary memory smoke passed")


if __name__ == "__main__":
    main()