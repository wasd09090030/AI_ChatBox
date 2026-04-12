"""剧本设计管理 v2 路由。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.service_context import ServiceContainer, get_services
from models.script_design import ScriptDesign, ScriptDesignCreate, ScriptDesignStatus, ScriptDesignUpdate

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


@router.get("/script-designs", response_model=List[ScriptDesign])
async def list_script_designs(
    world_id: Optional[str] = Query(default=None),
    status: Optional[ScriptDesignStatus] = Query(default=None),
    services: ServiceContainer = Depends(get_services),
):
    """功能：查询并返回剧本 designs列表。"""
    return services.script_design_app.list_script_designs(world_id=world_id, status=status)


@router.post("/script-designs", response_model=ScriptDesign)
async def create_script_design(
    payload: ScriptDesignCreate,
    services: ServiceContainer = Depends(get_services),
):
    """功能：创建剧本设计。"""
    try:
        return services.script_design_app.create_script_design(payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "World not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/script-designs/{script_design_id}", response_model=ScriptDesign)
async def get_script_design(script_design_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：获取剧本设计。"""
    script_design = services.script_design_app.get_script_design(script_design_id)
    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    return script_design


@router.put("/script-designs/{script_design_id}", response_model=ScriptDesign)
async def update_script_design(
    script_design_id: str,
    payload: ScriptDesignUpdate,
    services: ServiceContainer = Depends(get_services),
):
    """功能：更新剧本设计。"""
    try:
        script_design = services.script_design_app.update_script_design(script_design_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    return script_design


@router.delete("/script-designs/{script_design_id}")
async def delete_script_design(script_design_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：删除剧本设计。"""
    result = services.script_design_app.delete_script_design(script_design_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    if result["blocked"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Script design is still bound to stories",
                "story_binding_count": result["story_binding_count"],
            },
        )
    return {"success": result["deleted"], "script_design_id": script_design_id}


@router.get("/script-designs/{script_design_id}/story-bindings")
async def get_script_design_story_bindings(
    script_design_id: str,
    services: ServiceContainer = Depends(get_services),
):
    """功能：获取剧本设计故事绑定。"""
    script_design = services.script_design_app.get_script_design(script_design_id)
    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    bindings = services.script_design_app.list_story_bindings(script_design_id)
    return {
        "script_design_id": script_design_id,
        "count": len(bindings),
        "items": bindings,
    }