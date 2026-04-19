"""故事生成可观测性应用辅助。

负责把生成结果转换为稳定的 metrics / analytics 载荷，避免路由层直接依赖
具体埋点实现或重复拼装观测字段。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from application.ports import AnalyticsSink, MetricsRecorder


def estimate_tokens(text: str) -> int:
    """CJK 感知的 token 估算兜底逻辑（provider usage 缺失时使用）。"""
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u30ff")
    latin = len(text) - cjk
    return max(1, int(cjk * 1.7 + latin * 0.25))


def _context_type(item: Any) -> str:
    """兼容读取上下文条目类型。"""
    if isinstance(item, dict):
        return str(item.get("type") or "")
    return str(getattr(item, "type", "") or "")


def _context_content(item: Any) -> str:
    """兼容读取上下文条目内容。"""
    if isinstance(item, dict):
        return str(item.get("content") or "")
    return str(getattr(item, "content", "") or "")


def build_observability_counters(response: Any) -> Dict[str, Any]:
    """从生成响应构建可观测性计数器。"""
    activation_logs = list(getattr(response, "activation_logs", None) or [])
    contexts = list(getattr(response, "contexts", None) or [])
    story_state_snapshot = getattr(response, "story_state_snapshot", None)

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
    ) or story_state_snapshot is not None
    story_state_clues_count = len((story_state_snapshot or {}).get("clues") or [])
    history_hits = sum(1 for item in contexts if _context_type(item) == "conversation_history")

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
    response: Any,
) -> Dict[str, Any]:
    """优先使用 provider usage 解析 token，缺失时回退估算。"""
    tokens_used = getattr(response, "tokens_used", None)
    contexts = list(getattr(response, "contexts", None) or [])
    output_text = str(getattr(response, "output_text", "") or "")

    if tokens_used and int(tokens_used.get("total_tokens", 0)) > 0:
        prompt_tokens = int(tokens_used.get("input_tokens", 0))
        completion_tokens = int(tokens_used.get("output_tokens", 0))
        total_tokens = int(tokens_used.get("total_tokens", prompt_tokens + completion_tokens))
        token_source = "provider_usage"
    else:
        prompt_tokens = estimate_tokens(request_user_input) + estimate_tokens(
            "".join(_context_content(item) for item in contexts)
        )
        completion_tokens = estimate_tokens(output_text)
        total_tokens = prompt_tokens + completion_tokens
        token_source = "estimated"
        setattr(
            response,
            "tokens_used",
            {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        )

    setattr(response, "token_source", token_source)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "token_source": token_source,
    }


def record_generation_success(
    *,
    metrics_recorder: MetricsRecorder,
    analytics_sink: AnalyticsSink,
    request_id: str,
    session_id: str,
    world_id: Optional[str],
    request_user_input: str,
    response: Any,
    request_total_time: float,
) -> Dict[str, Any]:
    """记录一次成功生成的 metrics 与 analytics。"""
    counters = build_observability_counters(response)
    metrics_recorder.record(
        api_version="v2",
        mode="generate",
        request_id=request_id,
        session_id=session_id,
        world_id=world_id,
        generation_time=float(getattr(response, "generation_time", 0.0) or 0.0),
        retrieved_context_count=len(getattr(response, "contexts", None) or []),
        retrieved_history_count=counters["history_hits"],
        activation_log_count=len(counters["activation_logs"]),
        rule_hit_count=counters["rule_hit_count"],
        vector_hit_count=counters["vector_hit_count"],
        budget_trim_dropped_count=counters["budget_trim_dropped_count"],
        summary_applied=counters["summary_applied"],
        summary_updated=counters["summary_updated"],
        story_state_updated=counters["story_state_updated"],
        story_state_clues_count=counters["story_state_clues_count"],
        request_total_time=request_total_time,
        success=True,
    )

    token_usage = resolve_token_usage(request_user_input=request_user_input, response=response)
    analytics_sink.record_event(
        event_type="story_generate",
        session_id=session_id,
        world_id=world_id,
        model=str(getattr(response, "model", "-") or "-"),
        success=True,
        generation_time=float(getattr(response, "generation_time", 0.0) or 0.0),
        prompt_tokens=token_usage["prompt_tokens"],
        completion_tokens=token_usage["completion_tokens"],
        total_tokens=token_usage["total_tokens"],
        token_source=token_usage["token_source"],
        vector_hits=counters["vector_hit_count"],
        retrieved_context_count=len(getattr(response, "contexts", None) or []),
    )
    return {
        "counters": counters,
        "token_usage": token_usage,
    }


def record_generation_failure(
    *,
    metrics_recorder: MetricsRecorder,
    analytics_sink: AnalyticsSink,
    request_id: str,
    session_id: str,
    world_id: Optional[str],
    model: Optional[str],
    request_total_time: float,
    error_type: str,
) -> None:
    """记录一次失败生成的 metrics 与 analytics。"""
    metrics_recorder.record(
        api_version="v2",
        mode="generate",
        request_id=request_id,
        session_id=session_id,
        world_id=world_id,
        generation_time=request_total_time,
        retrieved_context_count=0,
        retrieved_history_count=0,
        request_total_time=request_total_time,
        success=False,
        error_type=error_type,
    )
    analytics_sink.record_event(
        event_type="story_generate",
        session_id=session_id,
        world_id=world_id,
        model=model or "-",
        success=False,
        generation_time=request_total_time,
        error_type=error_type,
    )
