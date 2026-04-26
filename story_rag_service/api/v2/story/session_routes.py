"""故事会话路由。

聚焦会话与消息生命周期：创建/读取会话、回滚最后消息、重生成上一轮回复。
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from application.memory import build_memory_update_event, persist_memory_update_events
from application.memory.events import build_memory_operation_id
from application.story_generation import (
    build_story_graph_request_payload,
    execute_story_graph_generation,
    load_or_create_story_session_context,
)
from api.dependencies.auth import get_current_user
from entity_state_response_serializer import (
    serialize_entity_state_collection,
    serialize_entity_state_rebuild_response,
)
from api.dependencies.world import StorySessionDependencies, get_story_session_dependencies
from api.v2.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    DeleteLastMessageResponse,
    EntityStateQueryParams,
    RegenerateRequest,
    SessionInfoResponse,
    V2GenerateResponse,
)
from models.entity_state import (
    EntityStateCollectionResponse,
    EntityStateRebuildResponsePayload,
)
from models.user import User

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)
# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


def _reconcile_session_memory_after_mutation(
    *,
    session_id: str,
    session_services: StorySessionDependencies,
    owner_user_id: str,
    source: str,
    operation_id: Optional[str] = None,
    sequence_start: int = 1,
    story_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Any]]:
    """在消息回滚后重建会话缓存、历史索引、摘要与实体状态。"""
    meta = session_services.session_manager.get_session_metadata(
        session_id,
        owner_user_id=owner_user_id,
    ) or {}
    world_id = meta.get("world_id")
    messages = session_services.session_manager.load_session_messages(
        session_id,
        limit=500,
        owner_user_id=owner_user_id,
    )
    # 先重建会话缓存，保证后续图执行读取的是最新消息视图。
    session_services.session_manager.rebuild_cached_context(session_id, messages)
    effective_story_id = story_id or session_services.story_runtime_manager.derive_story_id(session_id)

    memory_updates: List[Dict[str, Any]] = [
        build_memory_update_event(
            session_id=session_id,
            memory_layer="episodic",
            action="rebuilt",
            source=source,
            memory_key="story_session_messages",
            title="会话上下文已根据最新消息重建",
            after={"message_count": len(messages)},
        )
    ]

    try:
        # 历史向量索引失败不阻断主流程，改为写失败事件。
        session_services.history_manager.rebuild_session_history(session_id, world_id, messages)
        memory_updates.append(
            build_memory_update_event(
                session_id=session_id,
                memory_layer="episodic",
                action="reindexed",
                source=source,
                memory_key="conversation_history_index",
                title="历史向量索引已重建",
                after={"indexed_message_count": len(messages)},
            )
        )
    except Exception as exc:
        memory_updates.append(
            build_memory_update_event(
                session_id=session_id,
                memory_layer="episodic",
                action="reindexed",
                source=source,
                memory_key="conversation_history_index",
                title="历史向量索引重建失败",
                reason=str(exc),
                status="failed",
            )
        )

    summary_reset = session_services.summary_memory_manager.delete_summary(session_id)
    if summary_reset:
        memory_updates.append(
            build_memory_update_event(
                session_id=session_id,
                memory_layer="semantic",
                action="reset",
                source=source,
                memory_key="conversation_summary",
                title="摘要记忆已重置",
                reason="消息历史发生回退，旧摘要不再可信",
            )
        )

    updates_to_persist = list(memory_updates)

    if session_services.entity_state_manager is not None and effective_story_id:
        try:
            completed_turns = sum(1 for message in messages if getattr(message, "role", None) == "assistant")
            if session_services.entity_state_event_repository is not None:
                session_services.entity_state_event_repository.delete_by_session_id_after_turn(
                    session_id,
                    completed_turns,
                )

            entity_rebuild = None
            if session_services.entity_state_event_replay_service is not None:
                entity_rebuild = session_services.entity_state_event_replay_service.replay_session_state(
                    story_id=effective_story_id,
                    session_id=session_id,
                    source=source,
                    operation_id=operation_id,
                    sequence_start=sequence_start + len(updates_to_persist),
                    source_turn_lte=completed_turns,
                    allow_empty_result=True,
                    persist=True,
                )

            if entity_rebuild is None or not entity_rebuild.rebuilt:
                entity_rebuild = session_services.entity_state_fallback_service.rebuild_session_state(
                    session_id=session_id,
                    story_id=effective_story_id,
                    world_id=world_id,
                    messages=messages,
                    source=source,
                    operation_id=operation_id,
                    sequence_start=sequence_start + len(updates_to_persist),
                )
            memory_updates.extend(entity_rebuild.memory_updates)
        except Exception as exc:
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="entity_state",
                    action="rebuilt",
                    source=source,
                    memory_key=effective_story_id,
                    title="实体状态重建失败",
                    reason=str(exc),
                    status="failed",
                )
            )
            updates_to_persist = list(memory_updates)

    persist_memory_update_events(
        updates_to_persist,
        operation_id=operation_id,
        sequence_start=sequence_start,
    )
    return memory_updates, messages


@router.post("/story/session", response_model=CreateSessionResponse)
async def create_story_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """创建故事会话。"""
    session_id = request.session_id or str(uuid.uuid4())
    load_or_create_story_session_context(
        session_store=session_services.session_manager,
        payload={
            "session_id": session_id,
            "world_id": request.world_id,
            "character_card_id": request.character_card_id,
            "persona_id": request.persona_id,
        },
        owner_user_id=current_user.id,
    )

    meta = session_services.session_manager.get_session_metadata(
        session_id,
        owner_user_id=current_user.id,
    )
    return CreateSessionResponse(
        session_id=session_id,
        world_id=request.world_id,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
        first_message=None,
        created_at=meta.get("created_at") if meta else None,
    )


@router.get("/story/session/{session_id}", response_model=SessionInfoResponse)
async def get_story_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """读取故事会话元数据。"""
    row = session_services.session_manager.get_session_metadata(
        session_id,
        owner_user_id=current_user.id,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return SessionInfoResponse(
        session_id=session_id,
        world_id=row.get("world_id"),
        character_card_id=row.get("character_card_id"),
        persona_id=row.get("persona_id"),
        first_message_sent=bool(row.get("first_message_sent")),
        created_at=row.get("created_at"),
        last_active_at=row.get("last_active_at"),
    )


@router.delete(
    "/story/session/{session_id}/messages/last",
    response_model=DeleteLastMessageResponse,
)
async def delete_last_message(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """删除最后一条消息并触发记忆一致性重建。"""
    deleted = session_services.session_manager.delete_last_message(
        session_id,
        owner_user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="No messages found for this session")

    operation_id = build_memory_operation_id("rollback")
    memory_updates, _ = _reconcile_session_memory_after_mutation(
        session_id=session_id,
        session_services=session_services,
        owner_user_id=current_user.id,
        source="rollback",
        operation_id=operation_id,
        sequence_start=1,
        story_id=session_services.story_runtime_manager.derive_story_id(session_id),
    )

    return DeleteLastMessageResponse(
        deleted=True,
        session_id=session_id,
        detail="Last message deleted",
        memory_updates=memory_updates,
    )


@router.post("/story/session/{session_id}/regenerate", response_model=V2GenerateResponse)
async def regenerate_last_response(
    session_id: str,
    request: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """删除最后一条助手消息，并基于最近用户输入重新生成。"""
    session_services.session_manager.delete_last_assistant_message(
        session_id,
        owner_user_id=current_user.id,
    )
    user_input = session_services.session_manager.get_last_user_message(
        session_id,
        owner_user_id=current_user.id,
    )
    if not user_input:
        raise HTTPException(status_code=400, detail="No user message found to regenerate from")

    # 回滚后先对齐缓存与数据库视图，再进入重生成。
    operation_id = build_memory_operation_id("regenerate")
    pre_generation_updates, _ = _reconcile_session_memory_after_mutation(
        session_id=session_id,
        session_services=session_services,
        owner_user_id=current_user.id,
        source="regenerate",
        operation_id=operation_id,
        sequence_start=1,
        story_id=request.story_id,
    )

    request_payload = build_story_graph_request_payload(
        request=request,
        session_id=session_id,
        user_input=user_input,
        memory_operation_id=operation_id,
        memory_operation_sequence_start=len(pre_generation_updates) + 1,
    )
    response = await execute_story_graph_generation(
        request_payload=request_payload,
        thread_id=session_id,
        user_id=current_user.id,
    )
    response.memory_updates = pre_generation_updates + list(response.memory_updates or [])
    return response


@router.get("/story/session/{session_id}/entity-state", response_model=EntityStateCollectionResponse)
async def get_session_entity_state(
    session_id: str,
    query: EntityStateQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """读取会话当前实体状态快照（兼容桥接，优先事件回放）。"""
    if session_services.session_manager.get_session_metadata(
        session_id,
        owner_user_id=current_user.id,
    ) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    effective_story_id = session_services.story_runtime_manager.derive_story_id(session_id)
    snapshot = session_services.entity_state_fallback_service.get_session_snapshot(
        session_id=session_id,
        story_id=effective_story_id,
        entity_type=query.entity_type,
        source="entity_state_session_snapshot_api",
    )
    return serialize_entity_state_collection(snapshot)


@router.post("/story/session/{session_id}/entity-state/rebuild", response_model=EntityStateRebuildResponsePayload)
async def rebuild_session_entity_state(
    session_id: str,
    story_id: Optional[str] = None,
    world_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session_services: StorySessionDependencies = Depends(get_story_session_dependencies),
):
    """基于持久化消息重建会话级实体状态。"""
    effective_story_id = story_id or session_services.story_runtime_manager.derive_story_id(session_id)
    if not effective_story_id:
        raise HTTPException(status_code=400, detail="story_id is required for this session")

    meta = session_services.session_manager.get_session_metadata(
        session_id,
        owner_user_id=current_user.id,
    ) or {}
    resolved_world_id = world_id or meta.get("world_id")
    messages = session_services.session_manager.load_session_messages(
        session_id,
        limit=500,
        owner_user_id=current_user.id,
    )
    completed_turns = sum(1 for message in messages if getattr(message, "role", None) == "assistant")

    if session_services.entity_state_event_replay_service is not None:
        replay_result = session_services.entity_state_event_replay_service.replay_session_state(
            story_id=effective_story_id,
            session_id=session_id,
            source="entity_state_session_rebuild_api",
            source_turn_lte=completed_turns,
            allow_empty_result=False,
            persist=True,
        )
        if replay_result.rebuilt:
            return serialize_entity_state_rebuild_response(replay_result)

    rebuild_result = session_services.entity_state_fallback_service.rebuild_session_state(
        session_id=session_id,
        story_id=effective_story_id,
        world_id=resolved_world_id,
        messages=messages,
        source="entity_state_session_rebuild_api",
    )
    return serialize_entity_state_rebuild_response(rebuild_result)
