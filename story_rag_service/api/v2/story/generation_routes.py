"""
Story generation endpoints.

Route handlers in this module only adapt HTTP <-> application calls.
Metrics and token logic are delegated to helpers for SRP.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import AsyncGenerator, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from application.memory.events import build_memory_operation_id
from api.service_context import ServiceContainer, get_services
from api.v2.schemas import (
    V2GenerateRequest,
    V2GenerateResponse,
    V2InputEnhancementPreviewRequest,
    V2InputEnhancementPreviewResponse,
)
from graph.story_v2.story_graph import run_story_graph
from models.story import StoryGenerationRequest
from services import analytics_service
from services.observability import metrics_recorder

from .generation_metrics import build_observability_counters, resolve_token_usage

logger = logging.getLogger(__name__)
router = APIRouter()
_CHOICE_LINE_RE = re.compile(r"^\[([ABC])\]\s*(.+)$")


def _validate_user_header_for_generation(user_id: Optional[str], *, provider: Optional[str], model: Optional[str]) -> None:
    """校验生成请求是否必须携带 X-User-ID。

    当请求显式指定 provider，或未指定 model（可能依赖用户默认模型）时，
    必须提供用户作用域标识，避免跨用户配置歧义。
    """
    # 显式 provider 或未传 model 时，可能依赖用户默认配置，必须携带用户作用域。
    if not user_id and (provider is not None or not (model or "").strip()):
        raise HTTPException(
            status_code=400,
            detail=(
                "X-User-ID header is required for story generation when provider is specified "
                "or model is omitted."
            ),
        )


def _extract_choices_and_text(raw_text: str) -> Tuple[List[str], str]:
    """从文本中提取 [A]/[B]/[C] 选项，并返回去标记后的正文。"""
    if not raw_text:
        return [], ""

    choices: List[str] = []
    kept_lines: List[str] = []
    for line in raw_text.splitlines():
        match = _CHOICE_LINE_RE.match(line.strip())
        if match:
            choice_text = match.group(2).strip()
            if choice_text:
                choices.append(choice_text)
            continue
        kept_lines.append(line)

    return choices, "\n".join(kept_lines).strip()


async def _inject_choices_for_stream(
    stream: AsyncGenerator[str, None],
    mode: Optional[str],
) -> AsyncGenerator[str, None]:
    """在 choices 模式下重写 SSE 完成事件。

    该函数会缓存增量 chunk，并在 `done=True` 时提取 [A]/[B]/[C] 选项，
    同时输出清洗后的 `generated_text` 与 `output_text`。
    """
    if (mode or "narrative") != "choices":
        async for event in stream:
            yield event
        return

    buffered_chunks: List[str] = []
    async for event in stream:
        if not event.startswith("data: "):
            yield event
            continue

        payload_text = event[6:].strip()
        try:
            payload = json.loads(payload_text)
        except Exception:
            yield event
            continue

        if payload.get("done") is False:
            chunk_text = str(payload.get("chunk") or "")
            if chunk_text:
                buffered_chunks.append(chunk_text)
            yield event
            continue

        if payload.get("done") is True:
            joined_text = "".join(buffered_chunks)
            source_text = str(payload.get("generated_text") or payload.get("output_text") or joined_text)
            choices, cleaned_text = _extract_choices_and_text(source_text)
            payload["generated_text"] = cleaned_text
            payload["output_text"] = cleaned_text
            payload["choices"] = choices
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            continue

        yield event


@router.post("/story/generate", response_model=V2GenerateResponse)
async def generate_story_v2(
    http_request: Request,
    request: V2GenerateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """非流式故事生成入口（v2）。

    路由层仅负责：请求校验、调用图执行、记录观测/分析事件、返回标准响应。
    """
    _validate_user_header_for_generation(user_id, provider=request.provider, model=request.model)
    start_time = time.perf_counter()
    thread_id = request.thread_id or request.session_id
    request_id = getattr(http_request.state, "request_id", "-")
    logger.info(
        "v2.generate start request_id=%s session_id=%s world_id=%s thread_id=%s",
        request_id,
        request.session_id,
        request.world_id,
        thread_id,
    )

    try:
        operation_id = build_memory_operation_id("generate")
        request_payload = request.model_dump()
        request_payload["memory_operation_id"] = operation_id
        request_payload["memory_operation_sequence_start"] = 1
        graph_state = await run_story_graph(
            {
                "request_payload": request_payload,
                "thread_id": thread_id,
                "user_id": user_id,
            }
        )
        response = V2GenerateResponse(**graph_state["v2_response"])
        request_total_time = time.perf_counter() - start_time

        counters = build_observability_counters(response)
        metrics_recorder.record(
            api_version="v2",
            mode="generate",
            request_id=request_id,
            session_id=request.session_id,
            world_id=request.world_id,
            generation_time=response.generation_time,
            retrieved_context_count=len(response.contexts),
            retrieved_history_count=counters["history_hits"],
            activation_log_count=len(counters["activation_logs"]),
            rule_hit_count=counters["rule_hit_count"],
            vector_hit_count=counters["vector_hit_count"],
            budget_trim_dropped_count=counters["budget_trim_dropped_count"],
            summary_applied=counters["summary_applied"],
            summary_updated=counters["summary_updated"],
            story_state_updated=counters["story_state_updated"],
            story_state_clues_count=counters["story_state_clues_count"],
            request_total_time=request_total_time,
            success=True,
        )

        token_usage = resolve_token_usage(request_user_input=request.user_input, response=response)
        analytics_service.record_event(
            event_type="story_generate",
            session_id=request.session_id,
            world_id=request.world_id,
            model=response.model,
            success=True,
            generation_time=response.generation_time,
            prompt_tokens=token_usage["prompt_tokens"],
            completion_tokens=token_usage["completion_tokens"],
            total_tokens=token_usage["total_tokens"],
            token_source=token_usage["token_source"],
            vector_hits=counters["vector_hit_count"],
            retrieved_context_count=len(response.contexts),
        )
        return response
    except Exception as exc:
        request_total_time = time.perf_counter() - start_time
        metrics_recorder.record(
            api_version="v2",
            mode="generate",
            request_id=request_id,
            session_id=request.session_id,
            world_id=request.world_id,
            generation_time=request_total_time,
            retrieved_context_count=0,
            retrieved_history_count=0,
            request_total_time=request_total_time,
            success=False,
            error_type=type(exc).__name__,
        )
        analytics_service.record_event(
            event_type="story_generate",
            session_id=request.session_id,
            world_id=request.world_id,
            model=request.model or "-",
            success=False,
            generation_time=request_total_time,
            error_type=type(exc).__name__,
        )
        logger.error("Error generating story via graph (v2): %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/story/input-enhancement/preview", response_model=V2InputEnhancementPreviewResponse)
async def preview_input_enhancement(
    request: V2InputEnhancementPreviewRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    services: ServiceContainer = Depends(get_services),
):
    """预览输入增强结果，不执行正式故事生成。"""
    session_context = services.session_manager.get_or_create_session(
        session_id=request.session_id,
        world_id=request.world_id,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
    )

    internal_request = StoryGenerationRequest(
        session_id=request.session_id,
        story_id=request.story_id,
        user_input=request.user_input,
        world_id=request.world_id,
        creation_mode=request.creation_mode,
        progress_intent=request.progress_intent,
        runtime_state_id=request.runtime_state_id,
        allow_state_transition=request.allow_state_transition,
        context=session_context,
        model=request.model,
        provider=request.provider,
        base_url=request.base_url,
        temperature=request.temperature,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
        selected_context_entry_ids=request.selected_context_entry_ids,
        rag_scope_entry_ids=[],
        script_design_id=request.script_design_id,
        active_stage_id=request.active_stage_id,
        active_event_id=request.active_event_id,
        follow_script_design=request.follow_script_design,
        principal_character_id=request.principal_character_id,
        dialogue_mode=request.dialogue_mode,
        dialogue_target=request.dialogue_target,
        dialogue_intent=request.dialogue_intent,
        dialogue_style_hint=request.dialogue_style_hint,
        force_dialogue_round=request.force_dialogue_round,
        focus_instruction=request.focus_instruction,
        focus_label=request.focus_label,
        enhance_input=True,
    )
    preview = await services.story_generator.preview_enhanced_input(internal_request, user_id=user_id)
    return V2InputEnhancementPreviewResponse(**preview)


@router.post("/story/generate/stream")
async def generate_story_stream_v2(
    request: V2GenerateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    services: ServiceContainer = Depends(get_services),
):
    """流式故事生成入口（SSE）。

    由 StoryGenerator 输出增量事件，并在 choices 模式下做最终事件重写。
    """
    _validate_user_header_for_generation(user_id, provider=request.provider, model=request.model)
    thread_id = request.thread_id or request.session_id

    # 会话获取/创建统一委托给 SessionManager。
    session_context = services.session_manager.get_or_create_session(
        session_id=thread_id,
        world_id=request.world_id,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
    )

    operation_id = build_memory_operation_id("generate")
    internal_request = StoryGenerationRequest(
        session_id=thread_id,
        story_id=request.story_id,
        user_input=request.user_input,
        world_id=request.world_id,
        creation_mode=request.creation_mode,
        progress_intent=request.progress_intent,
        runtime_state_id=request.runtime_state_id,
        allow_state_transition=request.allow_state_transition,
        context=session_context,
        model=request.model,
        provider=request.provider,
        base_url=request.base_url,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        style=request.style,
        language=request.language,
        character_card_id=request.character_card_id,
        persona_id=request.persona_id,
        authors_note=request.authors_note,
        mode=request.mode or "narrative",
        instruction=request.instruction,
        selected_context_entry_ids=request.selected_context_entry_ids,
        rag_scope_entry_ids=[],
        script_design_id=request.script_design_id,
        active_stage_id=request.active_stage_id,
        active_event_id=request.active_event_id,
        follow_script_design=request.follow_script_design,
        principal_character_id=request.principal_character_id,
        dialogue_mode=request.dialogue_mode,
        dialogue_target=request.dialogue_target,
        dialogue_intent=request.dialogue_intent,
        dialogue_style_hint=request.dialogue_style_hint,
        force_dialogue_round=request.force_dialogue_round,
        focus_instruction=request.focus_instruction,
        focus_label=request.focus_label,
        enhance_input=request.enhance_input,
        memory_operation_id=operation_id,
        memory_operation_sequence_start=1,
    )

    stream = services.story_generator.generate_story_stream(internal_request, user_id=user_id)
    return StreamingResponse(
        _inject_choices_for_stream(stream, request.mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
