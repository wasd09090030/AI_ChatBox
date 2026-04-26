"""
V2 roleplay routes (CharacterCard / Persona / StoryState).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies.auth import get_current_user
from api.dependencies.world import RoleplayDependencies, get_roleplay_dependencies
from models.roleplay import PersonaProfile, PersonaProfileCreate, PersonaProfileUpdate, StoryState, StoryStateUpdate
from models.user import User

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()

@router.get("/roleplay/personas", response_model=List[PersonaProfile])
async def list_personas(
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """返回人格卡列表。"""
    return roleplay_services.roleplay_manager.list_personas(owner_user_id=current_user.id)


@router.post("/roleplay/personas", response_model=PersonaProfile)
async def create_persona(
    payload: PersonaProfileCreate,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """创建人格卡。"""
    return roleplay_services.roleplay_manager.create_persona(
        payload,
        owner_user_id=current_user.id,
    )


@router.get("/roleplay/personas/{persona_id}", response_model=PersonaProfile)
async def get_persona(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """按 ID 获取人格卡。"""
    persona = roleplay_services.roleplay_manager.get_persona(
        persona_id,
        owner_user_id=current_user.id,
    )
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.put("/roleplay/personas/{persona_id}", response_model=PersonaProfile)
async def update_persona(
    persona_id: str,
    payload: PersonaProfileUpdate,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """更新人格卡。"""
    persona = roleplay_services.roleplay_manager.update_persona(
        persona_id,
        payload,
        owner_user_id=current_user.id,
    )
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.delete("/roleplay/personas/{persona_id}")
async def delete_persona(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """删除人格卡。"""
    deleted = roleplay_services.roleplay_manager.delete_persona(
        persona_id,
        owner_user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {"success": True, "id": persona_id}


@router.get("/roleplay/story-state/{session_id}", response_model=StoryState)
async def get_story_state(
    session_id: str,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """按会话 ID 读取故事状态。"""
    state = roleplay_services.roleplay_manager.get_story_state(
        session_id,
        owner_user_id=current_user.id,
    )
    if state is None:
        raise HTTPException(status_code=404, detail="Story state not found")
    return state


@router.put("/roleplay/story-state/{session_id}", response_model=StoryState)
async def upsert_story_state(
    session_id: str,
    payload: StoryStateUpdate,
    current_user: User = Depends(get_current_user),
    roleplay_services: RoleplayDependencies = Depends(get_roleplay_dependencies),
):
    """按会话 ID 新增或更新故事状态。"""
    return roleplay_services.roleplay_manager.upsert_story_state(
        session_id,
        payload,
        owner_user_id=current_user.id,
    )
