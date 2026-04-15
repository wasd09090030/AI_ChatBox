"""摘要记忆更新辅助函数。

提供同步/异步两条摘要更新路径，并在必要时回退到规则摘要，
保证 semantic 层在 LLM 不可用或更新条件未满足时仍然可用。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.story import StoryContext


def build_summary_snapshot(context: StoryContext, world_id: Optional[str]) -> Dict[str, Any]:
    """基于近期消息构建规则摘要快照。

    用于低成本兜底：不依赖额外 LLM，总能产出可写入的 summary_text/key_facts。
    """
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

    # 仅截取最近 3 组 user/assistant 消息，平衡时效与冗余。
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
    """同步更新摘要记忆。

    仅在 should_update 命中时执行 upsert，避免每轮都重写语义层。
    """
    if not summary_memory_manager or not summary_memory_enabled:
        return None

    current_turn = len(context.messages) // 2
    if not summary_memory_manager.should_update(session_id, current_turn):
        # 未达到更新窗口时直接复用现有摘要，降低写放大。
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
    """异步更新摘要记忆，优先使用 LLM 总结。

    回退策略：LLM 路径失败或返回空时，自动降级为规则摘要路径。
    """
    if not summary_memory_manager or not summary_memory_enabled:
        return None

    current_turn = len(context.messages) // 2
    if not summary_memory_manager.should_update(session_id, current_turn):
        return summary_memory_manager.get_summary(session_id)

    merged_summary = None
    if llm is not None:
        # 仅截取最近 12 条消息做摘要，控制 LLM 总结成本。
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
