"""知识库 v2 路由。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.service_context import ServiceContainer, get_services
from models.lorebook import Character, Event, Location, LorebookEntry, LorebookType

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


class UpdateEntryRequest(BaseModel):
    """更新 lorebook 条目请求（按类型复用创建 payload）。"""
    entry_type: str  # 'character' | 'location' | 'event'
    world_id: str
    data: Dict[str, Any]


class BulkImportItem(BaseModel):
    """作用：定义 BulkImportItem 数据结构，用于约束字段语义与序列化格式。"""
    entry_type: str  # 'character' | 'location' | 'event'
    data: Dict[str, Any]


class BulkImportRequest(BaseModel):
    """作用：定义 BulkImportRequest 数据结构，用于约束字段语义与序列化格式。"""
    entries: List[BulkImportItem]


@router.get("/lorebook/entries")
async def list_lorebook_entries(
    world_id: Optional[str] = Query(default=None),
    services: ServiceContainer = Depends(get_services),
):
    """功能：查询并返回知识库条目列表。"""
    entries = services.lorebook_manager.get_all_entries(world_id=world_id)
    return {
        "entries": entries,
        "count": len(entries),
        "world_id": world_id,
    }


@router.post("/worlds/{world_id}/lorebook/character")
async def create_world_character(
    world_id: str,
    character: Character,
    services: ServiceContainer = Depends(get_services),
):
    """功能：创建世界观角色。"""
    result = services.world_app.create_character_in_world(world_id, character)
    if result is None:
        raise HTTPException(status_code=404, detail="World not found")
    return result


@router.post("/worlds/{world_id}/lorebook/location")
async def create_world_location(
    world_id: str,
    location: Location,
    services: ServiceContainer = Depends(get_services),
):
    """功能：创建世界观地点。"""
    result = services.world_app.create_location_in_world(world_id, location)
    if result is None:
        raise HTTPException(status_code=404, detail="World not found")
    return result


@router.post("/worlds/{world_id}/lorebook/event")
async def create_world_event(
    world_id: str,
    event: Event,
    services: ServiceContainer = Depends(get_services),
):
    """功能：创建世界观事件。"""
    result = services.world_app.create_event_in_world(world_id, event)
    if result is None:
        raise HTTPException(status_code=404, detail="World not found")
    return result


@router.delete("/lorebook/entry/{entry_id}")
async def delete_lorebook_entry(entry_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：删除知识库条目。"""
    deleted = services.lorebook_manager.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lorebook entry not found")
    return {
        "success": True,
        "entry_id": entry_id,
    }


@router.put("/lorebook/entry/{entry_id}")
async def update_lorebook_entry(
    entry_id: str,
    request: UpdateEntryRequest,
    services: ServiceContainer = Depends(get_services),
):
    """更新已有 lorebook 条目（删除后用同 ID 重建）。"""
    entry_type = request.entry_type.lower()
    world_id = request.world_id
    data = request.data

    try:
        if entry_type == "character":
            model = Character(**data)
            new_entry = model.to_lorebook_entry(world_id)
        elif entry_type == "location":
            model = Location(**data)
            new_entry = model.to_lorebook_entry(world_id)
        elif entry_type == "event":
            model = Event(**data)
            new_entry = model.to_lorebook_entry(world_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown entry_type: {entry_type}")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    success = services.lorebook_manager.update_entry(entry_id, new_entry)
    if not success:
        raise HTTPException(status_code=404, detail="Lorebook entry not found")
    return {"success": True, "entry_id": entry_id}


@router.post("/worlds/{world_id}/lorebook/bulk-import")
async def bulk_import_lorebook_entries(
    world_id: str,
    request: BulkImportRequest,
    services: ServiceContainer = Depends(get_services),
):
    """从 JSON 批量导入 lorebook 条目。"""
    results = {"success": [], "failed": []}

    for item in request.entries:
        entry_type = item.entry_type.lower()
        data = item.data
        try:
            if entry_type == "character":
                model = Character(**data)
                entry = model.to_lorebook_entry(world_id)
            elif entry_type == "location":
                model = Location(**data)
                entry = model.to_lorebook_entry(world_id)
            elif entry_type == "event":
                model = Event(**data)
                entry = model.to_lorebook_entry(world_id)
            else:
                results["failed"].append({"name": data.get("name", "?"), "reason": f"Unknown type: {entry_type}"})
                continue

            services.lorebook_manager.create_entry(entry)
            results["success"].append(data.get("name", "?"))
        except Exception as exc:
            results["failed"].append({"name": data.get("name", "?"), "reason": str(exc)})

    return {
        "imported": len(results["success"]),
        "failed": len(results["failed"]),
        "details": results,
    }
