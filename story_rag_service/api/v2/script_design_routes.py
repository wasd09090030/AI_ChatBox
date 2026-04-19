"""剧本设计管理 v2 路由。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.world import ScriptDesignDependencies, get_script_design_dependencies
from models.script_design import ScriptDesign, ScriptDesignCreate, ScriptDesignStatus, ScriptDesignUpdate

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


@router.get("/script-designs", response_model=List[ScriptDesign])
async def list_script_designs(
    world_id: Optional[str] = Query(default=None),
    status: Optional[ScriptDesignStatus] = Query(default=None),
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """按 world/status 条件查询剧本设计列表。"""
    return script_services.script_design_app.list_script_designs(world_id=world_id, status=status)


@router.post("/script-designs", response_model=ScriptDesign)
async def create_script_design(
    payload: ScriptDesignCreate,
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """创建剧本设计。

    `World not found` 映射为 404，其余校验错误映射为 400。
    """
    try:
        return script_services.script_design_app.create_script_design(payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "World not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/script-designs/{script_design_id}", response_model=ScriptDesign)
async def get_script_design(
    script_design_id: str,
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """按 ID 获取单个剧本设计。"""
    script_design = script_services.script_design_app.get_script_design(script_design_id)
    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    return script_design


@router.put("/script-designs/{script_design_id}", response_model=ScriptDesign)
async def update_script_design(
    script_design_id: str,
    payload: ScriptDesignUpdate,
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """更新剧本设计。

    参数非法返回 400；目标不存在返回 404。
    """
    try:
        script_design = script_services.script_design_app.update_script_design(script_design_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    return script_design


@router.delete("/script-designs/{script_design_id}")
async def delete_script_design(
    script_design_id: str,
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """删除剧本设计。

    若仍绑定故事则返回 409，并附带绑定数量。
    """
    result = script_services.script_design_app.delete_script_design(script_design_id)
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
    script_services: ScriptDesignDependencies = Depends(get_script_design_dependencies),
):
    """返回指定剧本设计的故事绑定清单。"""
    script_design = script_services.script_design_app.get_script_design(script_design_id)
    if script_design is None:
        raise HTTPException(status_code=404, detail="Script design not found")
    bindings = script_services.script_design_app.list_story_bindings(script_design_id)
    return {
        "script_design_id": script_design_id,
        "count": len(bindings),
        "items": bindings,
    }
