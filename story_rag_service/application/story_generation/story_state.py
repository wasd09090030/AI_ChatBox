"""故事状态更新辅助。

收敛 Story Graph 中的剧情状态派生与裁剪策略，避免节点函数直接承载
细节规则。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from models.roleplay import StoryStateUpdate


def extract_clue_candidates(user_input: str) -> List[str]:
    """从用户输入中提取线索候选。"""
    quoted = re.findall(r'“([^”]{2,24})”|"([^"]{2,24})"|《([^》]{2,24})》', user_input)
    merged_quoted = [part for group in quoted for part in group if part]
    if merged_quoted:
        return list(dict.fromkeys(merged_quoted[:3]))

    chunks = re.split(r"[，。！？、；,.!?;:\s]+", user_input)
    candidates = [chunk.strip() for chunk in chunks if 2 <= len(chunk.strip()) <= 24]
    return list(dict.fromkeys(candidates[:3]))


def derive_story_state_update(existing_state: Any, user_input: str) -> StoryStateUpdate:
    """根据用户输入与已有状态构建新的 StoryStateUpdate。"""
    chapter = getattr(existing_state, "chapter", None) or "第一幕"
    objective = getattr(existing_state, "objective", None) or f"围绕“{user_input[:24]}”推进当前主线"
    conflict = getattr(existing_state, "conflict", None) or "推进目标时遭遇阻力与信息不对称"

    clues = list(getattr(existing_state, "clues", []) or [])
    for clue in extract_clue_candidates(user_input):
        if clue not in clues:
            clues.append(clue)
    clues = clues[-8:]

    metadata = dict(getattr(existing_state, "metadata", {}) or {})
    metadata["last_user_input"] = user_input[:120]

    return StoryStateUpdate(
        chapter=chapter,
        objective=objective,
        conflict=conflict,
        clues=clues,
        metadata=metadata,
    )


def update_story_state_snapshot(
    *,
    roleplay_manager: Any,
    session_id: str,
    user_input: str,
    story_state_mode: Optional[str],
    story_state_enabled: bool,
) -> Optional[Dict[str, Any]]:
    """按策略更新并返回剧情状态快照。"""
    if not story_state_enabled:
        return None

    normalized_mode = (story_state_mode or "off").lower()
    if normalized_mode == "off":
        return None

    existing_state = roleplay_manager.get_story_state(session_id)
    update_payload = derive_story_state_update(existing_state, user_input)
    if normalized_mode == "light" and update_payload.clues:
        update_payload.clues = update_payload.clues[-4:]

    updated_state = roleplay_manager.upsert_story_state(session_id, update_payload)
    return updated_state.model_dump()
