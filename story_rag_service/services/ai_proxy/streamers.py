"""
各协议下的流式输出实现。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _build_openai_compat_payload(
    *,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    include_usage: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if include_usage:
        payload["stream_options"] = {"include_usage": True}
    return payload


def _should_retry_without_stream_options(status_code: int, body_text: str) -> bool:
    if status_code not in {400, 422}:
        return False
    normalized = (body_text or "").lower()
    if "stream_options" not in normalized:
        return False
    retry_markers = [
        "stream = true",
        "stream=true",
        "include_usage",
        "invalid_request_error",
        "unsupported",
    ]
    return any(marker in normalized for marker in retry_markers)


def _update_usage_from_openai_chunk(
    usage: Dict[str, Any],
    usage_sink: Optional[Dict[str, int]],
) -> None:
    """从 OpenAI 兼容 usage 字段提取 token 信息并写入 usage_sink。"""
    if not isinstance(usage, dict):
        return

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    if usage_sink is not None and total_tokens > 0:
        usage_sink["input_tokens"] = prompt_tokens
        usage_sink["output_tokens"] = completion_tokens
        usage_sink["total_tokens"] = total_tokens


def _update_usage_from_anthropic_chunk(
    usage: Dict[str, Any],
    usage_sink: Optional[Dict[str, int]],
) -> None:
    """从 Anthropic usage 字段提取 token 信息并写入 usage_sink。"""
    if not isinstance(usage, dict) or usage_sink is None:
        return

    input_tokens = int(usage.get("input_tokens", usage_sink.get("input_tokens", 0)) or 0)
    output_tokens = int(usage.get("output_tokens", usage_sink.get("output_tokens", 0)) or 0)
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
    if total_tokens > 0:
        usage_sink["input_tokens"] = input_tokens
        usage_sink["output_tokens"] = output_tokens
        usage_sink["total_tokens"] = total_tokens


async def stream_openai_compat(
    *,
    api_key: str,
    base_url: str,
    chat_path: str,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    usage_sink: Optional[Dict[str, int]] = None,
) -> AsyncGenerator[str, None]:
    """流式请求 OpenAI 兼容协议接口。"""
    url = f"{base_url}{chat_path}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        include_usage_candidates = [True, False]
        for attempt_idx, include_usage in enumerate(include_usage_candidates):
            payload = _build_openai_compat_payload(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                include_usage=include_usage,
            )
            try:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        body_text = body.decode(errors="replace")
                        if include_usage and _should_retry_without_stream_options(response.status_code, body_text):
                            logger.warning(
                                "OpenAI-compat provider rejected stream_options; retrying without include_usage"
                            )
                            continue
                        logger.error("OpenAI-compat error %s: %s", response.status_code, body)
                        raise ValueError(
                            f"API error {response.status_code}: {body_text[:200]}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            _update_usage_from_openai_chunk(chunk.get("usage"), usage_sink)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError) as exc:
                            logger.debug("Skipped unparseable SSE chunk: %s (%s)", data, exc)
                    return
            except httpx.TimeoutException as exc:
                if attempt_idx == len(include_usage_candidates) - 1:
                    raise ValueError("Request timeout. Please try again.") from exc
                continue


async def stream_anthropic(
    *,
    api_key: str,
    base_url: str,
    chat_path: str,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    usage_sink: Optional[Dict[str, int]] = None,
) -> AsyncGenerator[str, None]:
    """流式请求 Anthropic 协议接口。"""
    url = f"{base_url}{chat_path}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    system_message = None
    turns = []
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        else:
            turns.append({"role": msg["role"], "content": msg["content"]})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": turns,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if system_message:
        payload["system"] = system_message

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error("Anthropic error %s: %s", response.status_code, body)
                    raise ValueError(
                        f"Anthropic API error {response.status_code}: "
                        f"{body.decode(errors='replace')[:200]}"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = line[6:]
                    try:
                        chunk = json.loads(data)
                        _update_usage_from_anthropic_chunk(chunk.get("usage"), usage_sink)
                        if chunk.get("type") == "content_block_delta":
                            content = chunk.get("delta", {}).get("text", "")
                            if content:
                                yield content
                        elif chunk.get("type") == "message_stop":
                            break
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.debug("Skipped unparseable Anthropic chunk: %s", exc)
        except httpx.TimeoutException as exc:
            raise ValueError("Request timeout. Please try again.") from exc
