"""
故事生成中的 RAG 检索编排逻辑。
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    _HAS_BM25 = True
except ImportError:
    _HAS_BM25 = False
    logger.warning("rank-bm25 未安装，混合检索将退回纯向量模式")

# ── P2-B: Cross-Encoder 精排（惰性加载） ─────────────────────────────────────
_cross_encoder_instance = None


def _get_cross_encoder():
    """惰性加载 Cross-Encoder 模型（首次调用约 1–2s，后续 ~0ms）。"""
    global _cross_encoder_instance
    if _cross_encoder_instance is None:
        try:
            from sentence_transformers import CrossEncoder
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            cache_dir = settings.huggingface_cache_dir
            _cross_encoder_instance = CrossEncoder(
                model_name_or_path=model_name,
                max_length=256,
                cache_folder=cache_dir,
            )
            logger.info("✅ Cross-Encoder 加载成功: %s", model_name)
        except Exception as exc:
            logger.warning("Cross-Encoder 加载失败，将跳过精排: %s", exc)
            _cross_encoder_instance = False  # sentinel: 不再重试
    return _cross_encoder_instance if _cross_encoder_instance else None


def _rerank_candidates(
    query: str,
    candidates: List[Tuple[str, float]],
    entry_lookup: Dict[str, Dict[str, Any]],
    top_n: int,
) -> List[Tuple[str, float]]:
    """用 Cross-Encoder 对候选重评分，返回 top_n 结果。"""
    encoder = _get_cross_encoder()
    if not encoder or not candidates:
        return candidates[:top_n]
    pairs = []
    valid_ids = []
    for eid, _ in candidates[:min(len(candidates), 10)]:
        entry = entry_lookup.get(eid)
        if entry:
            content = entry.get("content", "")
            pairs.append((query, content[:512]))
            valid_ids.append(eid)
    if not pairs:
        return candidates[:top_n]
    scores = encoder.predict(pairs)
    reranked = sorted(zip(valid_ids, scores), key=lambda x: x[1], reverse=True)
    return [(eid, float(s)) for eid, s in reranked[:top_n]]


def _parse_int(value: Any, default: int = 0) -> int:
    """将任意值安全转换为整数。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _entry_identity(entry: Dict[str, Any]) -> str:
    """构建条目唯一身份键，用于规则命中与向量命中去重。"""
    metadata = entry.get("metadata") or {}
    return (
        str(metadata.get("_chroma_id") or metadata.get("id") or "")
        or f"{entry.get('type', 'unknown')}::{entry.get('name', 'unknown')}::{entry.get('content', '')[:64]}"
    )


def _normalize_entry_id(entry: Dict[str, Any]) -> str:
    """提取条目的规范化 ID（用于作用域过滤）。"""
    metadata = entry.get("metadata") or {}
    return str(entry.get("id") or metadata.get("id") or metadata.get("_chroma_id") or "").strip()


def _extract_keywords(entry: Dict[str, Any]) -> List[str]:
    """从条目元数据中提取关键词。"""
    metadata = entry.get("metadata") or {}
    raw_keywords = metadata.get("keywords")
    keywords: List[str] = []

    if isinstance(raw_keywords, str):
        keywords.extend([item.strip() for item in raw_keywords.split(",") if item and item.strip()])
    elif isinstance(raw_keywords, list):
        keywords.extend([str(item).strip() for item in raw_keywords if str(item).strip()])

    trigger_keywords = metadata.get("trigger_keywords")
    if isinstance(trigger_keywords, str):
        keywords.extend([item.strip() for item in trigger_keywords.split(",") if item and item.strip()])
    elif isinstance(trigger_keywords, list):
        keywords.extend([str(item).strip() for item in trigger_keywords if str(item).strip()])

    if not keywords and entry.get("name"):
        keywords.append(str(entry["name"]).strip())

    return list(dict.fromkeys([item for item in keywords if item]))


# ── P2: BM25 + RRF 混合检索 ──────────────────────────────────────────────────

_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def _tokenize(text: str) -> List[str]:
    """简单分词：CJK 单字切分 + 空格分割西文。"""
    tokens: List[str] = []
    buf: List[str] = []
    for ch in text.lower():
        if _CJK_PATTERN.match(ch):
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isalnum() or ch == '-':
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
    if buf:
        tokens.append("".join(buf))
    return tokens


def _bm25_rank_entries(
    all_entries: List[Dict[str, Any]],
    query: str,
) -> List[Tuple[int, float]]:
    """对全部条目执行 BM25 评分，返回 (index, score) 列表（降序）。"""
    if not _HAS_BM25 or not all_entries:
        return []
    corpus = [
        _tokenize(f"{e.get('name', '')} {e.get('content', '')}") for e in all_entries
    ]
    if not corpus or all(len(doc) == 0 for doc in corpus):
        return []
    bm25 = BM25Okapi(corpus)
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(idx, float(s)) for idx, s in ranked if s > 0]


def _rrf_fuse(
    *ranked_lists: List[Tuple[str, float]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion：合并多路排序结果。

    每路输入为 [(entry_id, score), ...]，按 score 降序排列。
    返回融合后的 [(entry_id, fused_score), ...]，降序。
    """
    fused: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (eid, _score) in enumerate(ranked):
            fused[eid] = fused.get(eid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


def build_retrieval_query(
    user_input: str,
    current_location: Optional[str],
    active_characters: Optional[List[str]],
) -> str:
    """根据用户输入与短期上下文构建检索查询。"""
    query = user_input
    if current_location:
        query += f" {current_location}"
    if active_characters:
        query += f" {' '.join(active_characters)}"
    return query


def _select_rule_contexts(
    *,
    all_entries: List[Dict[str, Any]],
    query: str,
    retrieval_budget: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], set]:
    """执行规则命中选择，返回命中上下文、日志和已选 ID 集合。"""
    query_lower = query.lower()
    rule_candidates = []
    for entry in all_entries:
        metadata_check = entry.get("metadata") or {}
        entry_enabled = entry.get("enabled", metadata_check.get("enabled", True))
        if not entry_enabled:
            continue
        probability = float(entry.get("probability", metadata_check.get("probability", 1.0)))
        if probability < 1.0 and random.random() > probability:
            continue

        keywords = _extract_keywords(entry)
        matched_keywords = [kw for kw in keywords if kw and kw.lower() in query_lower]
        if not matched_keywords:
            continue

        metadata = entry.get("metadata") or {}
        priority = _parse_int(metadata.get("priority"), default=_parse_int(metadata.get("importance"), default=0))
        rule_candidates.append((priority, max(len(item) for item in matched_keywords), entry, matched_keywords))

    rule_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    rule_budget = min(max(1, retrieval_budget // 2), len(rule_candidates)) if retrieval_budget > 0 else 0

    selected_entry_ids = set()
    selected_contexts: List[Dict[str, Any]] = []
    activation_logs: List[Dict[str, Any]] = []

    for index, (priority, _, entry, matched_keywords) in enumerate(rule_candidates[:rule_budget]):
        entry_id = _entry_identity(entry)
        if entry_id in selected_entry_ids:
            continue

        selected_entry_ids.add(entry_id)
        metadata = dict(entry.get("metadata") or {})
        metadata["retrieval_source"] = "rule"
        metadata["matched_keywords"] = matched_keywords
        metadata["priority"] = priority
        insertion_position = entry.get("insertion_position", metadata.get("insertion_position", "after_char"))

        selected_contexts.append(
            {
                "name": entry.get("name", "Unknown"),
                "type": entry.get("type", "unknown"),
                "content": entry.get("content", ""),
                "relevance_score": 0.0,
                "insertion_position": insertion_position,
                "metadata": metadata,
            }
        )
        activation_logs.append(
            {
                "source": "rule",
                "entry_name": entry.get("name", "Unknown"),
                "entry_type": entry.get("type", "unknown"),
                "priority": priority,
                "matched_keywords": matched_keywords,
                "budget_slot": index + 1,
            }
        )

    dropped_rule_count = len(rule_candidates) - len(selected_contexts)
    if dropped_rule_count > 0:
        activation_logs.append(
            {
                "source": "rule",
                "event": "budget_trim",
                "dropped_count": dropped_rule_count,
                "selected_count": len(selected_contexts),
            }
        )

    return selected_contexts, activation_logs, selected_entry_ids


def _select_explicit_contexts(
    *,
    lorebook_manager: Any,
    selected_entry_ids: List[str],
    world_id: Optional[str],
    allowed_entry_ids: Optional[set[str]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], set]:
    """按用户显式选择的 entry id 组装上下文。

    该分支优先级最高：命中的条目会先进入结果集，并标记 `retrieval_source=explicit`。
    """
    if not selected_entry_ids:
        return [], [], set()

    explicit_entries = lorebook_manager.get_entries_by_ids(selected_entry_ids, world_id=world_id)
    if allowed_entry_ids is not None:
        explicit_entries = [
            item for item in explicit_entries if _normalize_entry_id(item) in allowed_entry_ids
        ]

    seen_ids: set[str] = set()
    contexts: List[Dict[str, Any]] = []
    logs: List[Dict[str, Any]] = []
    for item in explicit_entries:
        entry_id = _entry_identity(item)
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        metadata = dict(item.get("metadata") or {})
        metadata["retrieval_source"] = "explicit"
        item["metadata"] = metadata
        item["relevance_score"] = float(item.get("relevance_score", 0.0))
        contexts.append(item)
        logs.append(
            {
                "source": "explicit",
                "selection_mode": "explicit",
                "entry_name": item.get("name", "Unknown"),
                "entry_type": item.get("type", "unknown"),
            }
        )
    return contexts, logs, seen_ids


def _select_vector_contexts(
    *,
    lorebook_manager: Any,
    query: str,
    world_id: Optional[str],
    retrieval_budget: int,
    selected_entry_ids: set,
    all_entries: Optional[List[Dict[str, Any]]] = None,
    allowed_entry_ids: Optional[set[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """混合检索：向量 + BM25 → RRF 融合，填充剩余预算。"""
    remaining_budget = max(0, retrieval_budget - len(selected_entry_ids))
    if remaining_budget <= 0:
        return [], []

    fetch_k = max(retrieval_budget * 2, 10)

    # ── 向量检索 ──
    vector_results = lorebook_manager.search_relevant_entries(
        query=query,
        world_id=world_id,
        k=fetch_k,
        score_threshold=settings.similarity_threshold,
    )
    vector_map: Dict[str, Dict[str, Any]] = {}
    vector_ranked: List[Tuple[str, float]] = []
    for item in vector_results:
        eid = _entry_identity(item)
        normalized_id = _normalize_entry_id(item)
        if allowed_entry_ids is not None and normalized_id not in allowed_entry_ids:
            continue
        if eid not in selected_entry_ids:
            vector_map[eid] = item
            vector_ranked.append((eid, float(item.get("relevance_score", 0.0))))

    # ── BM25 检索（仅 rank-bm25 可用时） ──
    bm25_ranked: List[Tuple[str, float]] = []
    bm25_map: Dict[str, Dict[str, Any]] = {}
    if _HAS_BM25 and all_entries:
        bm25_index_scores = _bm25_rank_entries(all_entries, query)
        for idx, score in bm25_index_scores[:fetch_k]:
            entry = all_entries[idx]
            eid = _entry_identity(entry)
            normalized_id = _normalize_entry_id(entry)
            if allowed_entry_ids is not None and normalized_id not in allowed_entry_ids:
                continue
            if eid not in selected_entry_ids:
                bm25_ranked.append((eid, score))
                if eid not in vector_map:
                    bm25_map[eid] = entry

    # ── RRF 融合 ──
    if bm25_ranked:
        fused = _rrf_fuse(vector_ranked, bm25_ranked, k=settings.rrf_k)
        logger.debug("🔀 RRF 融合: vector=%d, bm25=%d → fused=%d", len(vector_ranked), len(bm25_ranked), len(fused))
    else:
        fused = [(eid, s) for eid, s in vector_ranked]

    # ── Cross-Encoder 精排（可选） ──
    all_lookup = {**vector_map, **bm25_map}
    if settings.enable_reranker and fused:
        fused = _rerank_candidates(query, fused, all_lookup, top_n=remaining_budget)
        logger.debug("🔬 Cross-Encoder 精排完成, top=%d", len(fused))

    # ── 按融合排名取 top-k ──
    selected_contexts: List[Dict[str, Any]] = []
    activation_logs: List[Dict[str, Any]] = []

    for eid, fused_score in fused:
        if len(selected_contexts) >= remaining_budget:
            break
        item = vector_map.get(eid) or bm25_map.get(eid)
        if not item:
            continue
        selected_entry_ids.add(eid)
        metadata = dict(item.get("metadata") or {})
        source = "hybrid" if (eid in vector_map and eid in bm25_map) else ("vector" if eid in vector_map else "bm25")
        metadata["retrieval_source"] = source
        metadata["rrf_score"] = round(fused_score, 4)
        item["metadata"] = metadata
        selected_contexts.append(item)
        activation_logs.append({
            "source": source,
            "entry_name": item.get("name", "Unknown"),
            "entry_type": item.get("type", "unknown"),
            "score": item.get("relevance_score", 0.0),
            "rrf_score": round(fused_score, 4),
        })

    return selected_contexts, activation_logs


def retrieve_rag_context(
    *,
    request: Any,
    context: Any,
    lorebook_manager: Any,
    history_manager: Optional[Any],
    recent_message_count: int,
    history_k: int,
    history_score_threshold: Optional[float] = None,
    assistant_weight: Optional[float] = None,
    log_prefix: str = "",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str], List[Dict[str, Any]]]:
    """执行完整 RAG 检索流程。

    执行顺序：
    1. 显式条目选择；
    2. 规则激活选择；
    3. 向量/BM25 混合补足预算；
    4. 可选历史对话检索。
    """
    world_id = getattr(request, "world_id", None)
    if not request.use_rag:
        return [], [], world_id, []
    allowed_entry_ids = {
        str(item).strip()
        for item in list(getattr(request, "rag_scope_entry_ids", []) or [])
        if str(item).strip()
    }
    allowed_entry_ids = allowed_entry_ids or None

    query = build_retrieval_query(
        user_input=request.user_input,
        current_location=getattr(context, "current_location", None),
        active_characters=getattr(context, "active_characters", None),
    )
    if log_prefix:
        logger.info("%sRAG query: %s...", log_prefix, query[:80])

    retrieval_budget = request.top_k or settings.top_k_results
    activation_logs: List[Dict[str, Any]] = []
    explicit_selected_contexts, explicit_logs, selected_entry_ids = _select_explicit_contexts(
        lorebook_manager=lorebook_manager,
        selected_entry_ids=list(getattr(request, "selected_context_entry_ids", []) or []),
        world_id=world_id,
        allowed_entry_ids=allowed_entry_ids,
    )
    activation_logs.extend(explicit_logs)
    rule_selected_contexts: List[Dict[str, Any]] = []

    all_entries: List[Dict[str, Any]] = []
    try:
        all_entries = (
            lorebook_manager.get_entries_by_world(world_id)
            if world_id
            else lorebook_manager.get_all_entries()
        )
        if allowed_entry_ids is not None:
            all_entries = [
                item for item in all_entries
                if _normalize_entry_id(item) in allowed_entry_ids
            ]
        rule_selected_contexts, rule_logs, selected_entry_ids = _select_rule_contexts(
            all_entries=all_entries,
            query=query,
            retrieval_budget=retrieval_budget,
        )
        selected_entry_ids.update({_entry_identity(item) for item in explicit_selected_contexts})
        activation_logs.extend(rule_logs)
    except Exception as exc:
        logger.warning("Rule activation fallback to vector-only: %s", exc)

    vector_selected_contexts, vector_logs = _select_vector_contexts(
        lorebook_manager=lorebook_manager,
        query=query,
        world_id=world_id,
        retrieval_budget=retrieval_budget,
        selected_entry_ids=selected_entry_ids,
        all_entries=all_entries,
        allowed_entry_ids=allowed_entry_ids,
    )
    activation_logs.extend(vector_logs)

    retrieved_contexts = explicit_selected_contexts + rule_selected_contexts + vector_selected_contexts

    retrieved_history: List[Dict[str, Any]] = []
    if history_manager and len(context.messages) > recent_message_count:
        current_turn = len(context.messages)
        max_historical_turn = current_turn - recent_message_count
        history_kwargs: Dict[str, Any] = {
            "query": query,
            "session_id": request.session_id,
            "world_id": world_id,
            "k": history_k,
            "max_turn": max_historical_turn,
        }
        if history_score_threshold is not None:
            history_kwargs["score_threshold"] = history_score_threshold
        if assistant_weight is not None:
            history_kwargs["assistant_weight"] = assistant_weight
        try:
            retrieved_history = history_manager.search_relevant_history(**history_kwargs)
        except Exception as exc:
            logger.error("Failed to retrieve history: %s", exc)
            retrieved_history = []

    return retrieved_contexts, retrieved_history, world_id, activation_logs
