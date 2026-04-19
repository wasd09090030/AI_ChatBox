"""故事生成 v2 路由。

本模块只负责 HTTP 协议适配、请求校验与响应封装：
1) 非流式生成走 story graph；
2) 流式生成走 StoryGenerator 的 SSE 管道；
3) 观测指标与 token 统计由独立 helper 处理。
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
from application.story_generation import (
    build_story_graph_request_payload,
    build_story_generation_request,
    execute_story_graph_generation,
    load_or_create_story_session_context,
    record_generation_failure,
    record_generation_success,
)
from api.dependencies.generation import StoryGenerationDependencies, get_story_generation_dependencies
from api.v2.schemas import (
    V2GenerateRequest,
    V2GenerateResponse,
    V2InputEnhancementPreviewRequest,
    V2InputEnhancementPreviewResponse,
)

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)
# FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()
# 匹配 choices 模式输出中的 [A]/[B]/[C] 选项行。
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
    generation_services: StoryGenerationDependencies = Depends(get_story_generation_dependencies),
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
        request_payload = build_story_graph_request_payload(
            request=request,
            session_id=request.session_id,
            user_input=request.user_input,
            memory_operation_id=operation_id,
            memory_operation_sequence_start=1,
        )
        response = await execute_story_graph_generation(
            request_payload=request_payload,
            thread_id=thread_id,
            user_id=user_id,
        )
        request_total_time = time.perf_counter() - start_time

        record_generation_success(
            metrics_recorder=generation_services.metrics_recorder,
            analytics_sink=generation_services.analytics_sink,
            request_id=request_id,
            session_id=request.session_id,
            world_id=request.world_id,
            request_user_input=request.user_input,
            response=response,
            request_total_time=request_total_time,
        )
        return response
    except Exception as exc:
        request_total_time = time.perf_counter() - start_time
        record_generation_failure(
            metrics_recorder=generation_services.metrics_recorder,
            analytics_sink=generation_services.analytics_sink,
            request_id=request_id,
            session_id=request.session_id,
            world_id=request.world_id,
            model=request.model or "-",
            request_total_time=request_total_time,
            error_type=type(exc).__name__,
        )
        logger.error("Error generating story via graph (v2): %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/story/input-enhancement/preview", response_model=V2InputEnhancementPreviewResponse)
async def preview_input_enhancement(
    request: V2InputEnhancementPreviewRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    generation_services: StoryGenerationDependencies = Depends(get_story_generation_dependencies),
):
    """预览输入增强结果，不执行正式故事生成。"""
    session_context = load_or_create_story_session_context(
        session_store=generation_services.session_manager,
        payload={
            "session_id": request.session_id,
            "world_id": request.world_id,
            "character_card_id": request.character_card_id,
            "persona_id": request.persona_id,
        },
    )

    internal_request = build_story_generation_request(
        request=request,
        session_context=session_context,
        enhance_input=True,
    )
    preview = await generation_services.story_generator.preview_enhanced_input(internal_request, user_id=user_id)
    return V2InputEnhancementPreviewResponse(**preview)


@router.post("/story/generate/stream")
async def generate_story_stream_v2(
    request: V2GenerateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    generation_services: StoryGenerationDependencies = Depends(get_story_generation_dependencies),
):
    """流式故事生成入口（SSE）。

    由 StoryGenerator 输出增量事件，并在 choices 模式下做最终事件重写。
    """
    _validate_user_header_for_generation(user_id, provider=request.provider, model=request.model)
    thread_id = request.thread_id or request.session_id

    session_context = load_or_create_story_session_context(
        session_store=generation_services.session_manager,
        payload={
            "session_id": thread_id,
            "world_id": request.world_id,
            "character_card_id": request.character_card_id,
            "persona_id": request.persona_id,
        },
    )

    operation_id = build_memory_operation_id("generate")
    internal_request = build_story_generation_request(
        request=request,
        session_context=session_context,
        session_id=thread_id,
        memory_operation_id=operation_id,
        memory_operation_sequence_start=1,
    )

    stream = generation_services.story_generator.generate_story_stream(internal_request, user_id=user_id)
    return StreamingResponse(
        _inject_choices_for_stream(stream, request.mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
