"""分析统计 v2 路由。

说明：统一使用 /stats/* 路径，避免被广告拦截规则误伤。
"""

from fastapi import APIRouter, Query

from services import analytics_service

router = APIRouter()


def _normalize_optional_query(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@router.get("/stats/overview")
async def get_analytics_overview(
    model: str | None = Query(default=None),
    world_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    """返回全量时段聚合统计。"""
    return analytics_service.get_overview(
        model=_normalize_optional_query(model),
        world_id=_normalize_optional_query(world_id),
        event_type=_normalize_optional_query(event_type),
    )


@router.get("/stats/daily")
async def get_analytics_daily(
    days: int = Query(default=7, ge=1, le=90),
    model: str | None = Query(default=None),
    world_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    """返回最近 N 天逐日统计。"""
    return analytics_service.get_daily_stats(
        days=days,
        model=_normalize_optional_query(model),
        world_id=_normalize_optional_query(world_id),
        event_type=_normalize_optional_query(event_type),
    )


@router.get("/stats/log")
async def get_recent_events(
    limit: int = Query(default=50, ge=1, le=500),
    model: str | None = Query(default=None),
    world_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    """返回最近分析事件列表。"""
    return {
        "events": analytics_service.get_recent_events(
            limit=limit,
            model=_normalize_optional_query(model),
            world_id=_normalize_optional_query(world_id),
            event_type=_normalize_optional_query(event_type),
        )
    }


@router.get("/stats/filter-options")
async def get_analytics_filter_options():
    """返回模型/世界/事件类型筛选项。"""
    return analytics_service.get_filter_options()
