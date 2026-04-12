"""
V2 roleplay routes (CharacterCard / Persona / StoryState).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.service_context import ServiceContainer, get_services
from models.roleplay import PersonaProfile, PersonaProfileCreate, PersonaProfileUpdate, StoryState, StoryStateUpdate

# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()

@router.get("/roleplay/personas", response_model=List[PersonaProfile])
async def list_personas(services: ServiceContainer = Depends(get_services)):
    """功能：查询并返回人格卡列表。"""
    return services.roleplay_manager.list_personas()


@router.post("/roleplay/personas", response_model=PersonaProfile)
async def create_persona(
    payload: PersonaProfileCreate,
    services: ServiceContainer = Depends(get_services),
):
    """功能：创建人格卡。"""
    return services.roleplay_manager.create_persona(payload)


@router.get("/roleplay/personas/{persona_id}", response_model=PersonaProfile)
async def get_persona(persona_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：获取人格卡。"""
    persona = services.roleplay_manager.get_persona(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.put("/roleplay/personas/{persona_id}", response_model=PersonaProfile)
async def update_persona(
    persona_id: str,
    payload: PersonaProfileUpdate,
    services: ServiceContainer = Depends(get_services),
):
    """功能：更新人格卡。"""
    persona = services.roleplay_manager.update_persona(persona_id, payload)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.delete("/roleplay/personas/{persona_id}")
async def delete_persona(persona_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：删除人格卡。"""
    deleted = services.roleplay_manager.delete_persona(persona_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {"success": True, "id": persona_id}


@router.get("/roleplay/story-state/{session_id}", response_model=StoryState)
async def get_story_state(session_id: str, services: ServiceContainer = Depends(get_services)):
    """功能：获取故事状态。"""
    state = services.roleplay_manager.get_story_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Story state not found")
    return state


@router.put("/roleplay/story-state/{session_id}", response_model=StoryState)
async def upsert_story_state(
    session_id: str,
    payload: StoryStateUpdate,
    services: ServiceContainer = Depends(get_services),
):
    """功能：新增或更新故事状态。"""
    return services.roleplay_manager.upsert_story_state(session_id, payload)
