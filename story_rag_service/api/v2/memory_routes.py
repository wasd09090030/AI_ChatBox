"""
V2 memory update journal query routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.service_context import ServiceContainer, get_services
from api.v2.schemas import (
    MemorySessionTimelineResponse,
    MemorySummaryStateResponse,
    MemoryUpdateJournalItem,
    MemoryUpdateJournalListResponse,
    StoryMemorySnapshotResponse,
)
from application.memory.journal import list_memory_update_events

router = APIRouter()


def _normalize_optional_query(value: Optional[str]) -> Optional[str]:
    """规范化可选查询参数：去空白，空字符串转 None。"""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_date_query(value: Optional[str], *, end_of_day: bool = False) -> Optional[str]:
    """规范化日期查询参数，支持 YYYY-MM-DD 与 ISO 字符串。"""
    normalized = _normalize_optional_query(value)
    if not normalized:
        return None

    try:
        if len(normalized) == 10:
            suffix = "T23:59:59.999999" if end_of_day else "T00:00:00"
            return f"{normalized}{suffix}"
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return normalized


def _derive_summary_state(
    *,
    current_summary: Optional[dict],
    items: list[MemoryUpdateJournalItem],
) -> MemorySummaryStateResponse:
    """根据语义层事件序列推导摘要状态机。"""
    semantic_items = [item for item in items if item.memory_layer == "semantic"]
    latest_semantic = semantic_items[0] if semantic_items else None

    if latest_semantic:
        if latest_semantic.action == "marked_stale" or latest_semantic.status == "stale":
            state = "stale"
        elif latest_semantic.action == "reset":
            state = "reset"
        elif latest_semantic.action == "created":
            state = "recreated" if any(item.action == "reset" for item in semantic_items[1:]) else "created"
        else:
            state = "created" if current_summary else "absent"
    else:
        state = "created" if current_summary else "absent"

    return MemorySummaryStateResponse(
        state=state,
        current_summary=current_summary,
        last_semantic_event=latest_semantic,
    )


@router.get("/memory-updates", response_model=MemoryUpdateJournalListResponse)
async def get_memory_updates(
    session_id: Optional[str] = Query(default=None),
    world_id: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    memory_layer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """按多条件分页查询记忆更新日志。"""
    return MemoryUpdateJournalListResponse(
        **list_memory_update_events(
            session_id=_normalize_optional_query(session_id),
            world_id=_normalize_optional_query(world_id),
            source=_normalize_optional_query(source),
            memory_layer=_normalize_optional_query(memory_layer),
            status=_normalize_optional_query(status),
            search=_normalize_optional_query(search),
            date_from=_normalize_date_query(date_from),
            date_to=_normalize_date_query(date_to, end_of_day=True),
            page=page,
            page_size=page_size,
        )
    )


@router.get(
    "/story/session/{session_id}/memory-updates",
    response_model=MemorySessionTimelineResponse,
)
async def get_session_memory_updates(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    services: ServiceContainer = Depends(get_services),
):
    """查询单会话的记忆时间线，并附带当前摘要状态。"""
    result = list_memory_update_events(
        session_id=session_id,
        page=page,
        page_size=page_size,
    )
    metadata = services.session_manager.get_session_metadata(session_id)
    if not metadata and not result["items"]:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    items = [MemoryUpdateJournalItem(**item) for item in result["items"]]
    current_summary = services.summary_memory_manager.get_summary(session_id)

    return MemorySessionTimelineResponse(
        session_id=session_id,
        world_id=(metadata or {}).get("world_id"),
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        summary_state=_derive_summary_state(current_summary=current_summary, items=items),
    )


@router.get(
    "/story/session/{session_id}/story-memory",
    response_model=StoryMemorySnapshotResponse,
)
async def get_story_memory_snapshot(
    session_id: str,
    story_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    services: ServiceContainer = Depends(get_services),
):
    """读取单会话统一故事记忆快照。"""
    metadata = services.session_manager.get_session_metadata(session_id)
    snapshot = services.story_memory_service.get_story_memory_snapshot(
        session_id=session_id,
        story_id=_normalize_optional_query(story_id),
        world_id=(metadata or {}).get("world_id"),
        timeline_page=page,
        timeline_page_size=page_size,
    )
    story_memory = snapshot.get("story_memory") or {}
    semantic_snapshot = ((story_memory.get("semantic") or {}).get("summary_memory_snapshot") or None)
    runtime_snapshot = ((story_memory.get("runtime") or {}).get("runtime_state_snapshot") or None)
    entity_snapshot = ((story_memory.get("entity") or {}).get("entity_state_snapshot") or None)
    if (
        not metadata
        and int(snapshot.get("timeline_total") or 0) <= 0
        and semantic_snapshot is None
        and runtime_snapshot is None
        and entity_snapshot is None
    ):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return StoryMemorySnapshotResponse(**snapshot)
