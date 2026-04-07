"""故事生成分析与可观测性辅助函数。"""

from __future__ import annotations

from typing import Any, Dict

from api.v2.schemas import V2GenerateResponse


def estimate_tokens(text: str) -> int:
    """CJK 感知的 token 估算兜底逻辑（provider usage 缺失时使用）。"""
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u30ff")
    latin = len(text) - cjk
    return max(1, int(cjk * 1.7 + latin * 0.25))


def build_observability_counters(response: V2GenerateResponse) -> Dict[str, Any]:
    """从生成响应构建可观测性计数器。"""
    activation_logs = response.activation_logs or []
    rule_hit_count = sum(
        1 for item in activation_logs if item.get("source") == "rule" and item.get("entry_name")
    )
    vector_hit_count = sum(
        1 for item in activation_logs if item.get("source") == "vector" and item.get("entry_name")
    )
    budget_trim_dropped_count = sum(
        int(item.get("dropped_count") or 0)
        for item in activation_logs
        if item.get("source") == "rule" and item.get("event") == "budget_trim"
    )
    summary_applied = any(
        item.get("source") == "summary_memory" and item.get("event") == "applied"
        for item in activation_logs
    )
    summary_updated = any(
        item.get("source") == "summary_memory" and item.get("event") == "updated"
        for item in activation_logs
    )
    story_state_updated = any(
        item.get("source") == "story_state" and item.get("event") == "updated"
        for item in activation_logs
    ) or response.story_state_snapshot is not None
    story_state_clues_count = len((response.story_state_snapshot or {}).get("clues") or [])
    history_hits = sum(1 for item in response.contexts if item.type == "conversation_history")

    return {
        "activation_logs": activation_logs,
        "history_hits": history_hits,
        "rule_hit_count": rule_hit_count,
        "vector_hit_count": vector_hit_count,
        "budget_trim_dropped_count": budget_trim_dropped_count,
        "summary_applied": summary_applied,
        "summary_updated": summary_updated,
        "story_state_updated": story_state_updated,
        "story_state_clues_count": story_state_clues_count,
    }


def resolve_token_usage(
    *,
    request_user_input: str,
    response: V2GenerateResponse,
) -> Dict[str, Any]:
    """优先使用 provider usage 解析 token，缺失时回退估算。"""
    if response.tokens_used and int(response.tokens_used.get("total_tokens", 0)) > 0:
        prompt_tokens = int(response.tokens_used.get("input_tokens", 0))
        completion_tokens = int(response.tokens_used.get("output_tokens", 0))
        total_tokens = int(
            response.tokens_used.get("total_tokens", prompt_tokens + completion_tokens)
        )
        token_source = "provider_usage"
    else:
        prompt_tokens = estimate_tokens(request_user_input) + estimate_tokens(
            "".join(item.content for item in response.contexts)
        )
        completion_tokens = estimate_tokens(response.output_text)
        total_tokens = prompt_tokens + completion_tokens
        token_source = "estimated"
        response.tokens_used = {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    response.token_source = token_source
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "token_source": token_source,
    }
