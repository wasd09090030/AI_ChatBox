"""v2 世界与故事管理路由。"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from application.memory.events import build_memory_operation_id
from entity_state_response_serializer import (
    serialize_entity_state_collection,
    serialize_entity_state_rebuild_response,
)
from api.dependencies.world import WorldStoryDependencies, get_world_story_dependencies
from api.v2.schemas import EntityStateQueryParams
from models.entity_state import (
    EntityStateCollectionResponse,
    EntityStateRebuildResponsePayload,
)
from models.stored_story import (
    StoryAdjustmentCommitRequest,
    StoryAdjustmentCommitResponse,
    StoryCreate,
    StoryProgressUpdate,
    StorySegmentRollbackResponse,
    StorySegmentCreate,
    StoryUpdate,
    StoredStory,
)
from models.story_runtime import ScriptRuntimeState, ScriptRuntimeStateUpdate
from models.world import World, WorldCreate, WorldUpdate

# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()
# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


@router.get("/worlds", response_model=List[World])
async def list_worlds(world_services: WorldStoryDependencies = Depends(get_world_story_dependencies)):
    """列出全部世界。"""
    return world_services.world_app.list_worlds()


@router.post("/worlds", response_model=World)
async def create_world(
    world_data: WorldCreate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """创建世界。"""
    return world_services.world_app.create_world(world_data)


@router.get("/worlds/{world_id}", response_model=World)
async def get_world(world_id: str, world_services: WorldStoryDependencies = Depends(get_world_story_dependencies)):
    """按 world_id 查询世界详情。"""
    world = world_services.world_app.get_world(world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.put("/worlds/{world_id}", response_model=World)
async def update_world(
    world_id: str,
    world_data: WorldUpdate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """更新世界。"""
    world = world_services.world_app.update_world(world_id, world_data)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.delete("/worlds/{world_id}")
async def delete_world(world_id: str, world_services: WorldStoryDependencies = Depends(get_world_story_dependencies)):
    """删除世界并触发关联数据级联清理。"""
    result = world_services.world_app.delete_world(world_id)
    if result is None:
        raise HTTPException(status_code=404, detail="World not found")
    return result


@router.get("/stories", response_model=List[StoredStory])
async def list_stories(
    world_id: Optional[str] = Query(default=None),
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """按可选 world_id 列出故事。"""
    return world_services.story_manager.list_stories(world_id=world_id)


@router.post("/stories", response_model=StoredStory)
async def create_story(
    story_data: StoryCreate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """创建故事。"""
    world = world_services.world_manager.get_world(story_data.world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world_services.story_manager.create_story(story_data, world.name)


@router.get("/stories/{story_id}", response_model=StoredStory)
async def get_story(story_id: str, world_services: WorldStoryDependencies = Depends(get_world_story_dependencies)):
    """按 story_id 查询故事。"""
    story = world_services.story_manager.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.put("/stories/{story_id}", response_model=StoredStory)
async def update_story(
    story_id: str,
    update_data: StoryUpdate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """更新故事元数据。"""
    story = world_services.story_manager.update_story(story_id, update_data)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/stories/{story_id}")
async def delete_story(story_id: str, world_services: WorldStoryDependencies = Depends(get_world_story_dependencies)):
    """删除故事并清理对应实体状态快照。"""
    deleted = world_services.story_manager.delete_story(story_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    world_services.entity_state_manager.delete_story_states(story_id)
    world_services.entity_state_event_repository.delete_by_story_id(story_id)
    return {"success": True, "story_id": story_id}


@router.post("/stories/{story_id}/segments", response_model=StoredStory)
async def add_story_segment(
    story_id: str,
    segment_data: StorySegmentCreate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """追加一个故事片段。"""
    story = world_services.story_manager.add_segment(story_id, segment_data)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/stories/{story_id}/segments/last", response_model=StorySegmentRollbackResponse)
async def delete_last_story_segment(
    story_id: str,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """回滚最后一个故事片段，并重建会话一致性状态。"""
    existing_story = world_services.story_manager.get_story(story_id)
    if existing_story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    # 尝试定位回滚后的目标运行时快照（前一片段或初始快照）。
    previous_runtime_snapshot = None
    if len(existing_story.segments) >= 2:
        previous_runtime_snapshot = existing_story.segments[-2].runtime_state_snapshot
    elif isinstance(existing_story.metadata.get("runtime_initial_snapshot"), dict):
        previous_runtime_snapshot = existing_story.metadata.get("runtime_initial_snapshot")

    try:
        story = world_services.story_manager.remove_last_segment(story_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    restored_runtime = None
    if story.metadata.get("runtime_state_id") or story.metadata.get("script_design_id"):
        try:
            restored_runtime = world_services.story_runtime_manager.restore_runtime_state(
                story=story,
                runtime_snapshot=previous_runtime_snapshot if isinstance(previous_runtime_snapshot, dict) else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if restored_runtime is not None:
        world_services.story_runtime_manager.sync_story_metadata(restored_runtime)
        story = world_services.story_manager.get_story(story_id) or story

    session_id = (
        restored_runtime.session_id
        if restored_runtime is not None and restored_runtime.session_id
        else f"story-{story_id}-v2"
    )
    rebuild_result = world_services.story_consistency_rebuild_service.rebuild_story_state(
        story=story,
        session_id=session_id,
        source="story_segment_rollback",
        operation_id=build_memory_operation_id("story_segment_rollback"),
        sequence_start=1,
        prefer_event_replay=True,
        replay_source_turn_lte=len(story.segments),
    )

    return StorySegmentRollbackResponse(
        story=story,
        runtime_state=restored_runtime,
        session_id=session_id,
        rebuild_summary_reset=bool(rebuild_result["summary_reset"]),
        rebuild_history_reindexed=bool(rebuild_result["history_reindexed"]),
        rebuild_entity_state_rebuilt=bool(rebuild_result.get("entity_state_rebuilt")),
        memory_updates=list(rebuild_result.get("memory_updates") or []),
        warnings=list(rebuild_result.get("warnings") or []),
    )


@router.post("/stories/{story_id}/adjustments/commit", response_model=StoryAdjustmentCommitResponse)
async def commit_story_adjustments(
    story_id: str,
    commit_data: StoryAdjustmentCommitRequest,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """批量提交片段改写并重建衍生状态。"""
    existing_story = world_services.story_manager.get_story(story_id)
    if existing_story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    if not commit_data.updates:
        raise HTTPException(status_code=400, detail="No segment updates provided")

    session_id = commit_data.session_id or f"story-{story_id}-v2"

    try:
        updated_story = world_services.story_manager.update_story_segments_content(story_id, commit_data.updates)
        if updated_story is None:
            raise HTTPException(status_code=404, detail="Story not found")

        rebuild_result = world_services.story_consistency_rebuild_service.rebuild_story_state(
            story=updated_story,
            session_id=session_id,
            source="story_adjustment_commit",
            operation_id=build_memory_operation_id("story_adjustment_commit"),
            sequence_start=1,
        )
        return StoryAdjustmentCommitResponse(
            story=updated_story,
            session_id=session_id,
            rebuild_summary_reset=bool(rebuild_result["summary_reset"]),
            rebuild_history_reindexed=bool(rebuild_result["history_reindexed"]),
            rebuild_entity_state_rebuilt=bool(rebuild_result.get("entity_state_rebuilt")),
            memory_updates=list(rebuild_result.get("memory_updates") or []),
            warnings=list(rebuild_result["warnings"]),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to commit story adjustments for story %s: %s", story_id, exc, exc_info=True)
        try:
            world_services.story_manager.save_story(existing_story)
            world_services.story_consistency_rebuild_service.rebuild_story_state(
                story=existing_story,
                session_id=session_id,
                source="story_adjustment_commit_rollback",
                operation_id=build_memory_operation_id("story_adjustment_commit_rollback"),
                sequence_start=1,
            )
        except Exception as rollback_exc:
            logger.error(
                "Failed to roll back story adjustment commit for story %s: %s",
                story_id,
                rollback_exc,
                exc_info=True,
            )
        raise HTTPException(status_code=500, detail="Failed to commit story adjustments") from exc


@router.put("/stories/{story_id}/progress", response_model=StoredStory)
async def update_story_progress(
    story_id: str,
    progress_data: StoryProgressUpdate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """更新故事剧本推进元数据。"""
    story = world_services.story_manager.update_story_progress(story_id, progress_data)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.get("/stories/{story_id}/runtime", response_model=ScriptRuntimeState)
async def get_story_runtime(
    story_id: str,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """获取故事运行时状态，不存在时按 metadata 延迟初始化。"""
    runtime_state = world_services.story_runtime_manager.get_runtime_state(story_id)
    if runtime_state is None:
        story = world_services.story_manager.get_story(story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")

        metadata = story.metadata or {}
        script_design_id = metadata.get("script_design_id")
        if not isinstance(script_design_id, str) or not script_design_id.strip():
            raise HTTPException(status_code=404, detail="Runtime state not found")

        session_id = f"story-{story_id}-v2"
        runtime_state = world_services.story_runtime_manager.ensure_runtime_state(
            story_id=story_id,
            session_id=session_id,
            world_id=story.world_id,
            script_design_id=script_design_id,
            creation_mode=(
                str(metadata.get("creation_mode"))
                if metadata.get("creation_mode") in {"improv", "scripted"}
                else ("scripted" if metadata.get("follow_script_design") is True else "improv")
            ),
            preferred_stage_id=metadata.get("active_stage_id") if isinstance(metadata.get("active_stage_id"), str) else None,
            preferred_event_id=metadata.get("active_event_id") if isinstance(metadata.get("active_event_id"), str) else None,
        )
        world_services.story_runtime_manager.sync_story_metadata(runtime_state)

    return runtime_state


@router.put("/stories/{story_id}/runtime", response_model=ScriptRuntimeState)
async def update_story_runtime(
    story_id: str,
    runtime_update: ScriptRuntimeStateUpdate,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """更新故事运行时状态并回写故事进度元数据。"""
    try:
        runtime_state = world_services.story_runtime_manager.update_runtime_state(story_id, runtime_update)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if runtime_state is None:
        raise HTTPException(status_code=404, detail="Runtime state not found")
    world_services.story_runtime_manager.sync_story_metadata(runtime_state)
    return runtime_state


@router.get("/stories/{story_id}/entity-state", response_model=EntityStateCollectionResponse)
async def get_story_entity_state(
    story_id: str,
    query: EntityStateQueryParams = Depends(),
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """读取故事当前实体状态快照（兼容桥接，优先事件回放）。"""
    story = world_services.story_manager.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    session_id = f"story-{story_id}-v2"
    runtime_state = world_services.story_runtime_manager.get_runtime_state(story_id)
    if runtime_state is not None and runtime_state.session_id:
        session_id = runtime_state.session_id

    snapshot = world_services.entity_state_fallback_service.get_story_snapshot(
        story_id=story_id,
        session_id=session_id,
        entity_type=query.entity_type,
        source="entity_state_story_snapshot_api",
    )
    return serialize_entity_state_collection(snapshot)


@router.post("/stories/{story_id}/entity-state/rebuild", response_model=EntityStateRebuildResponsePayload)
async def rebuild_story_entity_state(
    story_id: str,
    session_id: Optional[str] = None,
    world_services: WorldStoryDependencies = Depends(get_world_story_dependencies),
):
    """基于持久化片段重建故事级实体状态。"""
    story = world_services.story_manager.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    runtime_state = world_services.story_runtime_manager.get_runtime_state(story_id)
    effective_session_id = (
        session_id
        or (runtime_state.session_id if runtime_state is not None and runtime_state.session_id else None)
        or f"story-{story_id}-v2"
    )
    if world_services.entity_state_event_replay_service is not None:
        replay_result = world_services.entity_state_event_replay_service.replay_story_state(
            story_id=story_id,
            session_id=effective_session_id,
            source="entity_state_story_rebuild_api",
            source_turn_lte=len(story.segments),
            allow_empty_result=False,
            persist=True,
        )
        if replay_result.rebuilt:
            return serialize_entity_state_rebuild_response(replay_result)

    rebuild_result = world_services.entity_state_fallback_service.rebuild_story_state(
        story=story,
        session_id=effective_session_id,
        runtime_state=runtime_state,
        source="entity_state_story_rebuild_api",
    )
    return serialize_entity_state_rebuild_response(rebuild_result)
