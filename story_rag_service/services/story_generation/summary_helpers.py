"""
摘要记忆更新辅助函数。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.story import StoryContext


def build_summary_snapshot(context: StoryContext, world_id: Optional[str]) -> Dict[str, Any]:
    """基于近期消息构建摘要快照。"""
    messages = context.messages
    last_turn = len(messages) // 2
    if not messages:
        return {
            "summary_text": "",
            "key_facts": [],
            "last_turn": last_turn,
        }

    user_messages = [msg.content.strip() for msg in messages if msg.role == "user" and msg.content.strip()]
    assistant_messages = [
        msg.content.strip() for msg in messages if msg.role == "assistant" and msg.content.strip()
    ]

    latest_user = user_messages[-3:]
    latest_assistant = assistant_messages[-3:]

    summary_lines = ["会话近期推进："]
    if latest_user:
        summary_lines.append("- 玩家近期行动: " + " / ".join([item[:48] for item in latest_user]))
    if latest_assistant:
        summary_lines.append("- 近期剧情反馈: " + " / ".join([item[:64] for item in latest_assistant]))

    key_facts: List[str] = []
    for item in latest_user + latest_assistant:
        snippet = item[:36].strip()
        if snippet:
            key_facts.append(snippet)

    return {
        "world_id": world_id,
        "summary_text": "\n".join(summary_lines),
        "key_facts": list(dict.fromkeys(key_facts))[:12],
        "entities": {},  # P1-B: 规则快照不做实体提取，LLM 路径补全
        "last_turn": last_turn,
    }


def maybe_update_summary_memory(
    *,
    summary_memory_manager,
    summary_memory_enabled: bool,
    session_id: str,
    world_id: Optional[str],
    context: StoryContext,
    activation_logs: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """同步更新摘要记忆。"""
    if not summary_memory_manager or not summary_memory_enabled:
        return None

    current_turn = len(context.messages) // 2
    if not summary_memory_manager.should_update(session_id, current_turn):
        return summary_memory_manager.get_summary(session_id)

    snapshot = build_summary_snapshot(context, world_id)
    merged_summary = summary_memory_manager.upsert_summary(
        session_id=session_id,
        world_id=world_id,
        new_summary_text=snapshot["summary_text"],
        new_key_facts=snapshot["key_facts"],
        last_turn=snapshot["last_turn"],
    )
    activation_logs.append(
        {
            "source": "summary_memory",
            "event": "updated",
            "last_turn": merged_summary.get("last_turn"),
            "facts_count": len(merged_summary.get("key_facts") or []),
        }
    )
    return merged_summary


async def async_maybe_update_summary_memory(
    *,
    summary_memory_manager,
    summary_memory_enabled: bool,
    session_id: str,
    world_id: Optional[str],
    context: StoryContext,
    activation_logs: List[Dict[str, Any]],
    llm: Any = None,
) -> Optional[Dict[str, Any]]:
    """异步更新摘要记忆，优先使用 LLM 总结。"""
    if not summary_memory_manager or not summary_memory_enabled:
        return None

    current_turn = len(context.messages) // 2
    if not summary_memory_manager.should_update(session_id, current_turn):
        return summary_memory_manager.get_summary(session_id)

    merged_summary = None
    if llm is not None:
        messages_snapshot = [{"role": msg.role, "content": msg.content} for msg in context.messages[-12:]]
        merged_summary = await summary_memory_manager.generate_llm_summary(
            messages_snapshot=messages_snapshot,
            session_id=session_id,
            world_id=world_id,
            last_turn=current_turn,
            llm=llm,
        )

    if merged_summary is None:
        snapshot = build_summary_snapshot(context, world_id)
        merged_summary = summary_memory_manager.upsert_summary(
            session_id=session_id,
            world_id=world_id,
            new_summary_text=snapshot["summary_text"],
            new_key_facts=snapshot["key_facts"],
            last_turn=snapshot["last_turn"],
        )

    if merged_summary:
        activation_logs.append(
            {
                "source": "summary_memory",
                "event": "updated",
                "last_turn": merged_summary.get("last_turn"),
                "facts_count": len(merged_summary.get("key_facts") or []),
            }
        )
    return merged_summary
