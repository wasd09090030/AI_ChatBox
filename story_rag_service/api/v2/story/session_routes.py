"""故事会话路由。

聚焦会话与消息生命周期：创建/读取会话、回滚最后消息、重生成上一轮回复。
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple, List, Dict, Any

from fastapi import APIRouter, Depends, Header, HTTPException

from application.memory import build_memory_update_event, persist_memory_update_events
from application.memory.events import build_memory_operation_id
from api.service_context import ServiceContainer, get_services
from api.v2.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    DeleteLastMessageResponse,
    EntityStateQueryParams,
    RegenerateRequest,
    SessionInfoResponse,
    V2GenerateResponse,
)
from models.entity_state import EntityStateCollection, EntityStateRebuildResponse
from graph.story_v2.story_graph import run_story_graph

logger = logging.getLogger(__name__)
router = APIRouter()


def _reconcile_session_memory_after_mutation(
    *,
    session_id: str,
    services: ServiceContainer,
    source: str,
    operation_id: Optional[str] = None,
    sequence_start: int = 1,
    story_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Any]]:
    """在消息回滚后重建会话缓存、历史索引、摘要与实体状态。"""
    meta = services.session_manager.get_session_metadata(session_id) or {}
    world_id = meta.get("world_id")
    messages = services.session_manager.load_session_messages(session_id, limit=500)
    # 先重建会话缓存，保证后续图执行读取的是最新消息视图。
    services.session_manager.rebuild_cached_context(session_id, messages)
    effective_story_id = story_id or services.story_runtime_manager.derive_story_id(session_id)

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
        services.history_manager.rebuild_session_history(session_id, world_id, messages)
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

    summary_reset = services.summary_memory_manager.delete_summary(session_id)
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

    if services.entity_state_manager is not None and effective_story_id:
        try:
            completed_turns = sum(1 for message in messages if getattr(message, "role", None) == "assistant")
            if services.entity_state_event_repository is not None:
                services.entity_state_event_repository.delete_by_session_id_after_turn(
                    session_id,
                    completed_turns,
                )

            entity_rebuild = None
            if services.entity_state_event_replay_service is not None:
                entity_rebuild = services.entity_state_event_replay_service.replay_session_state(
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
                entity_rebuild = services.entity_state_manager.rebuild_session_state(
                    session_id=session_id,
                    story_id=effective_story_id,
                    world_id=world_id,
                    messages=messages,
                    persist=True,
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
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    services: ServiceContainer = Depends(get_services),
):
    """创建故事会话。"""
    _ = user_id  # Reserved for future ownership checks.

    session_id = request.session_id or str(uuid.uuid4())
    services.session_manager.get_or_create_session(
        session_id=session_id,
        world_id=request.world_id,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
    )

    meta = services.session_manager.get_session_metadata(session_id)
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
    services: ServiceContainer = Depends(get_services),
):
    """读取故事会话元数据。"""
    row = services.session_manager.get_session_metadata(session_id)
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
    services: ServiceContainer = Depends(get_services),
):
    """删除最后一条消息并触发记忆一致性重建。"""
    deleted = services.session_manager.delete_last_message(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No messages found for this session")

    operation_id = build_memory_operation_id("rollback")
    memory_updates, _ = _reconcile_session_memory_after_mutation(
        session_id=session_id,
        services=services,
        source="rollback",
        operation_id=operation_id,
        sequence_start=1,
        story_id=services.story_runtime_manager.derive_story_id(session_id),
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
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    services: ServiceContainer = Depends(get_services),
):
    """删除最后一条助手消息，并基于最近用户输入重新生成。"""
    services.session_manager.delete_last_assistant_message(session_id)
    user_input = services.session_manager.get_last_user_message(session_id)
    if not user_input:
        raise HTTPException(status_code=400, detail="No user message found to regenerate from")

    # 回滚后先对齐缓存与数据库视图，再进入重生成。
    operation_id = build_memory_operation_id("regenerate")
    pre_generation_updates, _ = _reconcile_session_memory_after_mutation(
        session_id=session_id,
        services=services,
        source="regenerate",
        operation_id=operation_id,
        sequence_start=1,
        story_id=request.story_id,
    )

    graph_state = await run_story_graph(
        {
            "request_payload": {
                "session_id": session_id,
                "story_id": request.story_id,
                "user_input": user_input,
                "creation_mode": request.creation_mode,
                "progress_intent": request.progress_intent,
                "runtime_state_id": request.runtime_state_id,
                "allow_state_transition": request.allow_state_transition,
                "model": request.model,
                "provider": request.provider,
                "base_url": request.base_url,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "persona_id": request.persona_id,
                "authors_note": request.authors_note,
                "mode": request.mode or "narrative",
                "instruction": request.instruction,
                "script_design_id": request.script_design_id,
                "active_stage_id": request.active_stage_id,
                "active_event_id": request.active_event_id,
                "follow_script_design": request.follow_script_design,
                "principal_character_id": request.principal_character_id,
                "dialogue_mode": request.dialogue_mode,
                "dialogue_target": request.dialogue_target,
                "dialogue_intent": request.dialogue_intent,
                "dialogue_style_hint": request.dialogue_style_hint,
                "force_dialogue_round": request.force_dialogue_round,
                "focus_instruction": request.focus_instruction,
                "focus_label": request.focus_label,
                "selected_context_entry_ids": request.selected_context_entry_ids,
                "memory_operation_id": operation_id,
                "memory_operation_sequence_start": len(pre_generation_updates) + 1,
            },
            "thread_id": session_id,
            "user_id": user_id,
        }
    )
    response = V2GenerateResponse(**graph_state["v2_response"])
    response.memory_updates = pre_generation_updates + list(response.memory_updates or [])
    return response


@router.get("/story/session/{session_id}/entity-state", response_model=EntityStateCollection)
async def get_session_entity_state(
    session_id: str,
    query: EntityStateQueryParams = Depends(),
    services: ServiceContainer = Depends(get_services),
):
    """读取会话当前实体状态快照。"""
    items = services.entity_state_manager.list_session_states(
        session_id,
        entity_type=query.entity_type,
    )
    return EntityStateCollection(
        session_id=session_id,
        entity_type=query.entity_type,
        items=items,
        total=len(items),
    )


@router.post("/story/session/{session_id}/entity-state/rebuild", response_model=EntityStateRebuildResponse)
async def rebuild_session_entity_state(
    session_id: str,
    story_id: Optional[str] = None,
    world_id: Optional[str] = None,
    services: ServiceContainer = Depends(get_services),
):
    """基于持久化消息重建会话级实体状态。"""
    effective_story_id = story_id or services.story_runtime_manager.derive_story_id(session_id)
    if not effective_story_id:
        raise HTTPException(status_code=400, detail="story_id is required for this session")

    meta = services.session_manager.get_session_metadata(session_id) or {}
    resolved_world_id = world_id or meta.get("world_id")
    messages = services.session_manager.load_session_messages(session_id, limit=500)
    completed_turns = sum(1 for message in messages if getattr(message, "role", None) == "assistant")

    if services.entity_state_event_replay_service is not None:
        replay_result = services.entity_state_event_replay_service.replay_session_state(
            story_id=effective_story_id,
            session_id=session_id,
            source="entity_state_session_rebuild_api",
            source_turn_lte=completed_turns,
            allow_empty_result=False,
            persist=True,
        )
        if replay_result.rebuilt:
            return replay_result

    return services.entity_state_manager.rebuild_session_state(
        session_id=session_id,
        story_id=effective_story_id,
        world_id=resolved_world_id,
        messages=messages,
        persist=True,
        source="entity_state_session_rebuild_api",
    )
