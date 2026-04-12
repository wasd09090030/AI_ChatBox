"""分析事件服务：持久化记录与聚合统计。

事件按 JSONL 追加写入 data/analytics.jsonl，并提供面板所需概览、日统计与筛选项。
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 路径变量 DATA_DIR，用于定位文件系统资源。
DATA_DIR = Path(__file__).parent.parent / "data"
# 变量 ANALYTICS_FILE，用于保存分析文件相关模块级状态。
ANALYTICS_FILE = DATA_DIR / "analytics.jsonl"

# 变量 _write_lock，用于保存 write lock 相关模块级状态。
_write_lock = Lock()


def _ensure_dir() -> None:
    """确保分析日志目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Write ───────────────────────────────────────────────────────────────────

def record_event(
    *,
    event_type: str,
    session_id: str = "-",
    world_id: Optional[str] = None,
    model: str = "-",
    success: bool = True,
    generation_time: float = 0.0,
    prompt_tokens_est: int = 0,
    completion_tokens_est: int = 0,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    token_source: str = "estimated",
    vector_hits: int = 0,
    retrieved_context_count: int = 0,
    error_type: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """向 JSONL 日志追加一条分析事件。"""
    _ensure_dir()
    # 向后兼容 token 字段：优先精确值，缺失时回退 *_est。
    normalized_prompt = int(prompt_tokens if prompt_tokens is not None else prompt_tokens_est)
    normalized_completion = int(completion_tokens if completion_tokens is not None else completion_tokens_est)
    normalized_total = int(total_tokens if total_tokens is not None else (normalized_prompt + normalized_completion))

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "session_id": session_id,
        "world_id": world_id or "",
        "model": model,
        "success": success,
        "generation_time": round(generation_time, 3),
        # 标准 token 字段（token_source=provider_usage 时更精确）。
        "prompt_tokens": normalized_prompt,
        "completion_tokens": normalized_completion,
        "total_tokens": normalized_total,
        "token_source": token_source,
        # 兼容字段：保持前端与历史面板读取不受影响。
        "prompt_tokens_est": normalized_prompt,
        "completion_tokens_est": normalized_completion,
        "total_tokens_est": normalized_total,
        "vector_hits": vector_hits,
        "retrieved_context_count": retrieved_context_count,
        "error_type": error_type or "",
    }
    if extra:
        event.update(extra)

    try:
        with _write_lock:
            with open(ANALYTICS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("analytics write failed: %s", exc)


# ── Read ────────────────────────────────────────────────────────────────────

def _matches_filters(
    event: Dict[str, Any],
    *,
    model: Optional[str] = None,
    world_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> bool:
    """判断单条事件是否命中过滤条件。"""
    if model and str(event.get("model", "")).strip() != model:
        return False
    if world_id and str(event.get("world_id", "")).strip() != world_id:
        return False
    if event_type and str(event.get("event_type", "")).strip() != event_type:
        return False
    return True


def _load_events(
    days: Optional[int] = None,
    *,
    model: Optional[str] = None,
    world_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """读取事件列表，并按时间与维度做可选过滤。"""
    if not ANALYTICS_FILE.exists():
        return []

    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    events: List[Dict[str, Any]] = []
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if cutoff is not None:
                        ts_str = ev.get("timestamp", "")
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts < cutoff:
                                continue
                        except ValueError:
                            pass
                    if not _matches_filters(ev, model=model, world_id=world_id, event_type=event_type):
                        continue
                    events.append(ev)
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.warning("analytics read failed: %s", exc)

    return events


def _read_token_value(event: Dict[str, Any], precise_key: str, estimated_key: str) -> int:
    """读取 token 数值，优先精确字段，缺失时回退估算字段。"""
    return int(event.get(precise_key, event.get(estimated_key, 0)) or 0)


def get_overview(
    *,
    model: Optional[str] = None,
    world_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """返回全量时间范围的聚合统计。"""
    events = _load_events(model=model, world_id=world_id, event_type=event_type)

    total = len(events)
    if total == 0:
        return {
            "total_requests": 0,
            "success_requests": 0,
            "error_requests": 0,
            "success_rate": 1.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_tokens_est": 0,
            "avg_input_tokens": 0.0,
            "avg_output_tokens": 0.0,
            "avg_total_tokens": 0.0,
            "provider_usage_rate": 0.0,
            "avg_generation_time": 0.0,
            "avg_vector_hits": 0.0,
            "avg_retrieved_context_count": 0.0,
            "active_sessions": 0,
            "active_worlds": 0,
            "model_distribution": {},
            "event_type_distribution": {},
            "world_distribution": {},
            "token_source_distribution": {},
        }

    success = sum(1 for e in events if e.get("success", True))
    total_input_tokens = sum(_read_token_value(e, "prompt_tokens", "prompt_tokens_est") for e in events)
    total_output_tokens = sum(_read_token_value(e, "completion_tokens", "completion_tokens_est") for e in events)
    total_tokens = sum(_read_token_value(e, "total_tokens", "total_tokens_est") for e in events)
    provider_usage_count = sum(1 for e in events if e.get("token_source") == "provider_usage")
    avg_gen = sum(e.get("generation_time", 0.0) for e in events) / total
    avg_vec = sum(e.get("vector_hits", 0) for e in events) / total
    avg_contexts = sum(e.get("retrieved_context_count", 0) for e in events) / total

    model_dist: Dict[str, int] = defaultdict(int)
    type_dist: Dict[str, int] = defaultdict(int)
    world_dist: Dict[str, int] = defaultdict(int)
    token_source_dist: Dict[str, int] = defaultdict(int)
    active_sessions = {
        str(e.get("session_id", "")).strip()
        for e in events
        if str(e.get("session_id", "")).strip() and str(e.get("session_id", "")).strip() != "-"
    }

    for e in events:
        model_dist[e.get("model", "-")] += 1
        type_dist[e.get("event_type", "-")] += 1
        token_source_dist[e.get("token_source") or "estimated"] += 1
        w = e.get("world_id", "")
        if w:
            world_dist[w] += 1

    return {
        "total_requests": total,
        "success_requests": success,
        "error_requests": total - success,
        "success_rate": round(success / total, 4),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "total_tokens_est": total_tokens,
        "avg_input_tokens": round(total_input_tokens / total, 2),
        "avg_output_tokens": round(total_output_tokens / total, 2),
        "avg_total_tokens": round(total_tokens / total, 2),
        "provider_usage_rate": round(provider_usage_count / total, 4),
        "avg_generation_time": round(avg_gen, 3),
        "avg_vector_hits": round(avg_vec, 2),
        "avg_retrieved_context_count": round(avg_contexts, 2),
        "active_sessions": len(active_sessions),
        "active_worlds": len(world_dist),
        "model_distribution": dict(model_dist),
        "event_type_distribution": dict(type_dist),
        "world_distribution": dict(world_dist),
        "token_source_distribution": dict(token_source_dist),
    }


def get_daily_stats(
    days: int = 7,
    *,
    model: Optional[str] = None,
    world_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """返回最近 N 天的逐日统计拆分。"""
    events = _load_events(days=days, model=model, world_id=world_id, event_type=event_type)

    # 先按 UTC 日期预建桶，保证无事件日期也会返回。
    buckets: Dict[str, Dict[str, Any]] = {}
    for i in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        buckets[day] = {
            "date": day,
            "requests": 0,
            "success": 0,
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "provider_usage_requests": 0,
            "estimated_usage_requests": 0,
            "tokens": 0,
            "tokens_est": 0,
            "vector_hits": 0,
            "retrieved_context_count": 0,
            "generation_time_total": 0.0,
        }

    for ev in events:
        ts_str = ev.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            day = ts.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            continue
        if day not in buckets:
            continue
        b = buckets[day]
        b["requests"] += 1
        if ev.get("success", True):
            b["success"] += 1
        else:
            b["errors"] += 1
        b["input_tokens"] += _read_token_value(ev, "prompt_tokens", "prompt_tokens_est")
        b["output_tokens"] += _read_token_value(ev, "completion_tokens", "completion_tokens_est")
        b["tokens_est"] += ev.get("total_tokens_est", 0)
        b["tokens"] += _read_token_value(ev, "total_tokens", "total_tokens_est")
        b["vector_hits"] += ev.get("vector_hits", 0)
        b["retrieved_context_count"] += ev.get("retrieved_context_count", 0)
        b["generation_time_total"] += ev.get("generation_time", 0.0)
        if ev.get("token_source") == "provider_usage":
            b["provider_usage_requests"] += 1
        else:
            b["estimated_usage_requests"] += 1

    result = []
    for b in buckets.values():
        b["avg_generation_time"] = (
            round(b["generation_time_total"] / b["requests"], 3) if b["requests"] else 0.0
        )
        b["success_rate"] = round(b["success"] / b["requests"], 4) if b["requests"] else 1.0
        b["avg_input_tokens"] = round(b["input_tokens"] / b["requests"], 2) if b["requests"] else 0.0
        b["avg_output_tokens"] = round(b["output_tokens"] / b["requests"], 2) if b["requests"] else 0.0
        b["avg_total_tokens"] = round(b["tokens"] / b["requests"], 2) if b["requests"] else 0.0
        b["avg_retrieved_context_count"] = (
            round(b["retrieved_context_count"] / b["requests"], 2) if b["requests"] else 0.0
        )
        result.append(b)
    return result


def get_recent_events(
    limit: int = 50,
    *,
    model: Optional[str] = None,
    world_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """返回最近 N 条事件（按时间倒序）。"""
    events = _load_events(model=model, world_id=world_id, event_type=event_type)
    return list(reversed(events[-limit:]))


def get_filter_options() -> Dict[str, List[Dict[str, Any]]]:
    """返回分析面板的可选筛选项及计数。"""
    events = _load_events()
    model_dist: Dict[str, int] = defaultdict(int)
    type_dist: Dict[str, int] = defaultdict(int)
    world_dist: Dict[str, int] = defaultdict(int)

    for event in events:
        model_name = str(event.get("model", "")).strip()
        if model_name:
            model_dist[model_name] += 1

        event_name = str(event.get("event_type", "")).strip()
        if event_name:
            type_dist[event_name] += 1

        world_name = str(event.get("world_id", "")).strip()
        if world_name:
            world_dist[world_name] += 1

    def _to_items(distribution: Dict[str, int]) -> List[Dict[str, Any]]:
        """将分布字典转换为按计数降序的数组结构。"""
        return [
            {"value": key, "count": value}
            for key, value in sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
        ]

    return {
        "models": _to_items(model_dist),
        "event_types": _to_items(type_dist),
        "world_ids": _to_items(world_dist),
    }
