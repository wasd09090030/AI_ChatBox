"""
Dependency-aware all-endpoint functional attempt runner.

Goal:
- Traverse all OpenAPI routes and attempt endpoint calls.
- Prepare business fixtures first (world/story/session/persona/etc.) to reduce false failures.
- Do not fail the run for business-level non-2xx responses (400/404/422...).
- Fail only for transport errors and 5xx responses.

Usage:
  python scripts/smoke_all_api_functional_attempt_20260410.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_TIMEOUT=40
  SMOKE_USER_ID=user_xxx
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
  SMOKE_INCLUDE_OPTIONAL_QUERY=false
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT", "40"))
USER_ID = os.getenv("SMOKE_USER_ID", "user_1773820783085_bk1gzshza")
PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek")
MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat")
INCLUDE_OPTIONAL_QUERY = os.getenv("SMOKE_INCLUDE_OPTIONAL_QUERY", "false").lower() in {"1", "true", "yes"}

DATE_TAG = time.strftime("%Y-%m-%d")
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "TestResult"
REPORT_JSON = REPORT_DIR / f"AllApiFunctional_Attempt_Run_{DATE_TAG}.json"
REPORT_MD = REPORT_DIR / f"AllApiFunctional_Attempt_Report_{DATE_TAG}.md"

HTTP_METHODS = ["get", "post", "put", "patch", "delete"]
PATH_PARAM_PATTERN = re.compile(r"\{([^{}]+)\}")


@dataclass
class FixtureContext:
    world_id: Optional[str] = None
    story_id: Optional[str] = None
    session_id: Optional[str] = None
    entry_id: Optional[str] = None
    persona_id: Optional[str] = None
    script_design_id: Optional[str] = None
    segment_id: Optional[str] = None
    provider: str = PROVIDER
    model: str = MODEL
    created: dict[str, str] = field(default_factory=dict)


@dataclass
class EndpointResult:
    method: str
    path: str
    probe_url_path: str
    operation_id: Optional[str]
    status: int
    outcome: str
    available: bool
    duration_ms: int
    body_required: bool
    query_params_used: dict[str, Any]
    request_body_preview: Any
    response_preview: Any
    note: Optional[str] = None
    error: Optional[str] = None


def _headers() -> dict[str, str]:
    return {"X-User-ID": USER_ID}


def _safe_json_response(response: httpx.Response) -> Any:
    if not response.text:
        return {}
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:500]}


def _shorten(value: Any, limit: int = 350) -> Any:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)
    if len(text) <= limit:
        return value
    return {"truncated": text[:limit]}


def _pick_first_id(payload: Any, candidates: list[str]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in candidates:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _pick_latest_segment_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        return None
    last_segment = segments[-1]
    if not isinstance(last_segment, dict):
        return None
    segment_id = last_segment.get("id")
    if isinstance(segment_id, str) and segment_id:
        return segment_id
    return None


def _create_world(client: httpx.Client, *, label: str = "AllApiProbe-World") -> Optional[str]:
    status, body, _, _ = _request(
        client,
        "POST",
        "/api/v2/worlds",
        json_body={
            "name": f"{label}-{uuid.uuid4().hex[:6]}",
            "description": "all endpoint functional attempt",
            "genre": "mystery",
        },
    )
    if status == 200:
        return _pick_first_id(body, ["id", "world_id"])
    return None


def _create_story(
    client: httpx.Client,
    ctx: FixtureContext,
    *,
    world_id: Optional[str] = None,
    label: str = "AllApiProbe-Story",
) -> Optional[str]:
    effective_world_id = world_id or ctx.world_id
    if not effective_world_id:
        return None

    status, body, _, _ = _request(
        client,
        "POST",
        "/api/v2/stories",
        json_body={
            "world_id": effective_world_id,
            "title": f"{label}-{uuid.uuid4().hex[:6]}",
            "metadata": {"creation_mode": "improv"},
        },
    )
    if status == 200:
        return _pick_first_id(body, ["id", "story_id"])
    return None


def _create_persona(client: httpx.Client, *, label: str = "Probe Persona") -> Optional[str]:
    status, body, _, _ = _request(
        client,
        "POST",
        "/api/v2/roleplay/personas",
        json_body={
            "name": f"{label} {uuid.uuid4().hex[:4]}",
            "description": "functional endpoint probe",
            "profile": {"tone": "neutral"},
        },
    )
    if status == 200:
        return _pick_first_id(body, ["persona_id", "id"])
    return None


def _create_script_design(
    client: httpx.Client,
    ctx: FixtureContext,
    *,
    world_id: Optional[str] = None,
    label: str = "Probe Script Design",
) -> Optional[str]:
    effective_world_id = world_id or ctx.world_id
    if not effective_world_id:
        return None

    status, body, _, _ = _request(
        client,
        "POST",
        "/api/v2/script-designs",
        json_body={
            "world_id": effective_world_id,
            "title": f"{label} {uuid.uuid4().hex[:4]}",
            "summary": "functional endpoint probe",
        },
    )
    if status in {200, 201}:
        return _pick_first_id(body, ["script_design_id", "id"])
    return None


def _create_story_segment(
    client: httpx.Client,
    story_id: str,
) -> Optional[str]:
    status, body, _, _ = _request(
        client,
        "POST",
        f"/api/v2/stories/{story_id}/segments",
        json_body={
            "prompt": "Write a short probe segment.",
            "content": "Probe segment content",
            "creation_mode": "improv",
        },
    )
    if status in {200, 201}:
        return _pick_first_id(body, ["segment_id"]) or _pick_latest_segment_id(body)
    return None


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
    stream_mode: bool = False,
) -> tuple[int, Any, Optional[str], int]:
    start = time.time()
    try:
        if stream_mode:
            with client.stream(method.upper(), f"{BASE_URL}{path}", headers=_headers(), params=params, json=json_body) as response:
                status = response.status_code
                chunks = 0
                done_seen = False
                sample_lines: list[str] = []
                for part in response.iter_text():
                    if not part:
                        continue
                    chunks += 1
                    sample_lines.append(part[:120])
                    if "\"done\": true" in part or "\"done\":true" in part:
                        done_seen = True
                        break
                    if chunks >= 30:
                        break
                elapsed = int((time.time() - start) * 1000)
                return status, {
                    "stream_chunks": chunks,
                    "done_seen": done_seen,
                    "sample": sample_lines[:8],
                }, None, elapsed

        response = client.request(method.upper(), f"{BASE_URL}{path}", headers=_headers(), params=params, json=json_body)
        elapsed = int((time.time() - start) * 1000)
        return response.status_code, _safe_json_response(response), None, elapsed
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        return 0, {}, f"{type(exc).__name__}: {exc}", elapsed


def _classify(status: int, error: Optional[str]) -> tuple[str, bool]:
    if error:
        return "FAIL", False
    if status >= 500 or status == 0:
        return "FAIL", False
    if 200 <= status < 300:
        return "PASS", True
    # Business-level non-2xx are recorded as WARN to avoid false failures.
    return "WARN", True


def _resolve_ref(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    if not ref.startswith("#/components/schemas/"):
        return schema
    key = ref.split("/")[-1]
    resolved = components.get(key)
    if isinstance(resolved, dict):
        return resolved
    return schema


def _sample_from_schema(schema: Optional[dict[str, Any]], components: dict[str, Any], depth: int = 0) -> Any:
    if not isinstance(schema, dict):
        return None
    if depth > 5:
        return None

    schema = _resolve_ref(schema, components)

    if schema.get("enum") and isinstance(schema["enum"], list):
        return schema["enum"][0]

    if "oneOf" in schema and isinstance(schema["oneOf"], list) and schema["oneOf"]:
        return _sample_from_schema(schema["oneOf"][0], components, depth + 1)

    if "anyOf" in schema and isinstance(schema["anyOf"], list) and schema["anyOf"]:
        return _sample_from_schema(schema["anyOf"][0], components, depth + 1)

    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in schema["allOf"]:
            r = _resolve_ref(part, components)
            if not isinstance(r, dict):
                continue
            merged["properties"].update(r.get("properties") or {})
            merged["required"].extend(r.get("required") or [])
        return _sample_from_schema(merged, components, depth + 1)

    schema_type = schema.get("type")
    fmt = schema.get("format")

    if schema_type == "string" or (schema_type is None and "properties" not in schema):
        if fmt == "uuid":
            return str(uuid.uuid4())
        if fmt == "email":
            return "probe@example.com"
        if fmt == "date-time":
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return "probe"

    if schema_type == "integer":
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, int):
            if isinstance(maximum, int) and minimum > maximum:
                return 1
            return minimum
        return 1

    if schema_type == "number":
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)):
            return float(minimum)
        return 1.0

    if schema_type == "boolean":
        return True

    if schema_type == "array":
        item_schema = schema.get("items") or {}
        item = _sample_from_schema(item_schema, components, depth + 1)
        return [item] if item is not None else []

    properties = schema.get("properties")
    if isinstance(properties, dict):
        required = set(schema.get("required") or [])
        obj: dict[str, Any] = {}
        for key, child in properties.items():
            if key in required or len(obj) < 3:
                sample = _sample_from_schema(child, components, depth + 1)
                if sample is not None:
                    obj[key] = sample
        return obj

    return {}


def _route_override(method: str, path: str, ctx: FixtureContext) -> Optional[dict[str, Any]]:
    method = method.upper()

    if method == "POST" and path == "/api/v2/worlds":
        return {
            "name": f"AllApiProbe-World-{uuid.uuid4().hex[:6]}",
            "description": "all endpoint functional attempt",
            "genre": "mystery",
        }

    if method == "POST" and path == "/api/v2/stories":
        return {
            "world_id": ctx.world_id,
            "title": f"AllApiProbe-Story-{uuid.uuid4().hex[:6]}",
            "metadata": {"creation_mode": "improv"},
        }

    if method == "POST" and path == "/api/v2/story/session":
        return {
            "session_id": ctx.session_id or "probe-session",
            "world_id": ctx.world_id,
        }

    if method == "POST" and path == "/api/v2/worlds/{world_id}/lorebook/character":
        return {
            "name": "Probe Character",
            "personality": "calm",
            "background": "functional smoke",
            "inventory": [],
            "current_location": "Probe Tower",
        }

    if method == "POST" and path == "/api/v2/roleplay/personas":
        return {
            "name": f"Probe Persona {uuid.uuid4().hex[:4]}",
            "description": "functional endpoint probe",
            "profile": {"tone": "neutral"},
        }

    if method == "POST" and path == "/api/v2/script-designs":
        return {
            "world_id": ctx.world_id,
            "title": f"Probe Script Design {uuid.uuid4().hex[:4]}",
            "summary": "functional endpoint probe",
        }

    if method == "POST" and path == "/api/v2/providers/test-connection":
        return {
            "provider": ctx.provider,
            "base_url": None,
        }

    if method == "POST" and path == "/api/v2/providers/config":
        return {
            "provider": ctx.provider,
        }

    if method == "POST" and path == "/api/v2/story/generate":
        return {
            "session_id": ctx.session_id,
            "story_id": ctx.story_id,
            "world_id": ctx.world_id,
            "provider": ctx.provider,
            "model": ctx.model,
            "mode": "narrative",
            "temperature": 0.3,
            "max_tokens": 80,
            "creation_mode": "improv",
            "progress_intent": "hold",
            "user_input": "Functional API probe: move the story forward in one short paragraph.",
        }

    if method == "POST" and path == "/api/v2/story/generate/stream":
        return {
            "session_id": ctx.session_id,
            "story_id": ctx.story_id,
            "world_id": ctx.world_id,
            "provider": ctx.provider,
            "model": ctx.model,
            "mode": "narrative",
            "temperature": 0.3,
            "max_tokens": 64,
            "creation_mode": "improv",
            "progress_intent": "hold",
            "user_input": "Functional stream probe.",
        }

    if method == "PUT" and path == "/api/v2/stories/{story_id}/progress":
        return {
            "script_design_id": ctx.script_design_id,
            "active_stage_id": None,
            "active_event_id": None,
            "follow_script_design": bool(ctx.script_design_id),
            "creation_mode": "scripted" if ctx.script_design_id else "improv",
        }

    if method == "POST" and path == "/api/v2/stories/{story_id}/segments":
        return {
            "prompt": "Write a short probe segment.",
            "content": "probe segment content",
            "creation_mode": "improv",
        }

    if method == "POST" and path == "/api/v2/stories/{story_id}/adjustments/commit":
        return {
            "session_id": ctx.session_id,
            "updates": [
                {
                    "segment_id": ctx.segment_id,
                    "content": "Probe segment content after adjustment.",
                }
            ],
        }

    if method == "POST" and path == "/api/v2/story/adjustments/polish":
        return {
            "story_id": ctx.story_id,
            "session_id": ctx.session_id,
            "segment_id": ctx.segment_id,
            "selected_text": "Probe segment content",
            "preset_key": "style_polish",
            "preset_instruction": "Polish the selected text while preserving meaning.",
            "world_id": ctx.world_id,
            "provider": ctx.provider,
            "model": ctx.model,
        }

    if method == "POST" and path == "/api/v2/story/session/{session_id}/regenerate":
        return {
            "story_id": ctx.story_id,
            "persona_id": ctx.persona_id,
            "provider": ctx.provider,
            "model": ctx.model,
            "temperature": 0.4,
            "max_tokens": 96,
            "mode": "narrative",
            "creation_mode": "improv",
            "progress_intent": "hold",
        }

    if method == "PUT" and path == "/api/v2/providers/default-selection":
        return {
            "provider": ctx.provider,
            "model": ctx.model,
        }

    if method == "PUT" and path == "/api/v2/providers/scene-models":
        return {
            "story_generation": {"provider": ctx.provider, "model": ctx.model},
            "input_enhancement": {"provider": ctx.provider, "model": ctx.model},
            "story_adjustment": {"provider": ctx.provider, "model": ctx.model},
        }

    if method == "PUT" and path == "/api/v2/lorebook/entry/{entry_id}":
        return {
            "entry_type": "character",
            "world_id": ctx.world_id,
            "data": {
                "name": "Probe Character Updated",
                "personality": "calm",
                "background": "functional smoke update",
                "inventory": [],
                "current_location": "Probe Tower",
            },
        }

    if method == "PUT" and path == "/api/v2/stories/{story_id}/runtime":
        return {
            "script_design_id": ctx.script_design_id,
            "creation_mode": "scripted" if ctx.script_design_id else "improv",
            "runtime_notes": "all_api_probe_runtime_update",
        }

    return None


def _resolve_path(path_template: str, ctx: FixtureContext) -> str:
    mapping = {
        "world_id": ctx.world_id,
        "story_id": ctx.story_id,
        "session_id": ctx.session_id,
        "entry_id": ctx.entry_id,
        "persona_id": ctx.persona_id,
        "script_design_id": ctx.script_design_id,
        "segment_id": ctx.segment_id,
        "provider": ctx.provider,
        "key": "probe-key",
    }

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = mapping.get(key)
        if value:
            return value
        if key.endswith("_id"):
            return f"probe-{key}"
        return "probe"

    return PATH_PARAM_PATTERN.sub(repl, path_template)


def _prepare_probe_target(
    client: httpx.Client,
    method: str,
    path: str,
    ctx: FixtureContext,
) -> tuple[str, list[tuple[str, str]]]:
    cleanup_calls: list[tuple[str, str]] = []

    if method == "DELETE" and path == "/api/v2/worlds/{world_id}":
        temp_world_id = _create_world(client, label="AllApiProbe-DeleteWorld")
        if temp_world_id:
            return f"/api/v2/worlds/{temp_world_id}", cleanup_calls

    if method == "DELETE" and path == "/api/v2/stories/{story_id}":
        temp_story_id = _create_story(client, ctx, label="AllApiProbe-DeleteStory")
        if temp_story_id:
            return f"/api/v2/stories/{temp_story_id}", cleanup_calls

    if method == "DELETE" and path == "/api/v2/roleplay/personas/{persona_id}":
        temp_persona_id = _create_persona(client, label="Delete Persona")
        if temp_persona_id:
            return f"/api/v2/roleplay/personas/{temp_persona_id}", cleanup_calls

    if method == "DELETE" and path == "/api/v2/script-designs/{script_design_id}":
        temp_script_design_id = _create_script_design(client, ctx, label="Delete Script Design")
        if temp_script_design_id:
            return f"/api/v2/script-designs/{temp_script_design_id}", cleanup_calls

    if method == "DELETE" and path == "/api/v2/stories/{story_id}/segments/last":
        temp_story_id = _create_story(client, ctx, label="AllApiProbe-SegmentRollback")
        if temp_story_id:
            temp_segment_id = _create_story_segment(client, temp_story_id)
            if temp_segment_id:
                cleanup_calls.append(("DELETE", f"/api/v2/stories/{temp_story_id}"))
                return f"/api/v2/stories/{temp_story_id}/segments/last", cleanup_calls

    if method == "GET" and path == "/api/client-storage/{key}":
        _request(
            client,
            "PUT",
            "/api/client-storage/probe-key",
            json_body={"value": "probe"},
        )
        return "/api/client-storage/probe-key", cleanup_calls

    if path == "/api/v2/stories/{story_id}/runtime" and ctx.story_id and ctx.script_design_id:
        _request(
            client,
            "PUT",
            f"/api/v2/stories/{ctx.story_id}/progress",
            json_body={
                "script_design_id": ctx.script_design_id,
                "follow_script_design": True,
                "creation_mode": "scripted",
            },
        )
        return _resolve_path(path, ctx), cleanup_calls

    return _resolve_path(path, ctx), cleanup_calls


def _build_query_params(
    operation: dict[str, Any],
    components: dict[str, Any],
    ctx: FixtureContext,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for item in operation.get("parameters") or []:
        if not isinstance(item, dict):
            continue
        if item.get("in") != "query":
            continue
        required = bool(item.get("required"))
        if not required and not INCLUDE_OPTIONAL_QUERY:
            continue
        name = str(item.get("name") or "")
        schema = item.get("schema") if isinstance(item.get("schema"), dict) else {}

        if name == "page":
            params[name] = 1
            continue
        if name == "page_size":
            params[name] = 10
            continue
        if name.endswith("_id"):
            resolved = getattr(ctx, name, None)
            params[name] = resolved or f"probe-{name}"
            continue

        sampled = _sample_from_schema(schema, components)
        if sampled is not None:
            params[name] = sampled

    return params


def _build_body(
    method: str,
    path: str,
    operation: dict[str, Any],
    components: dict[str, Any],
    ctx: FixtureContext,
) -> tuple[Optional[dict[str, Any]], bool]:
    override = _route_override(method, path, ctx)
    if override is not None:
        return override, True

    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None, False

    content = request_body.get("content")
    if not isinstance(content, dict):
        return None, bool(request_body)

    media = content.get("application/json")
    if not isinstance(media, dict):
        # Unsupported body media types are still allowed to run; likely to WARN.
        return None, True

    schema = media.get("schema") if isinstance(media.get("schema"), dict) else {}
    sampled = _sample_from_schema(schema, components)
    if isinstance(sampled, dict):
        return sampled, True
    return None, True


def _prepare_fixtures(client: httpx.Client, ctx: FixtureContext) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []

    def call(method: str, path: str, body: Optional[dict[str, Any]] = None) -> tuple[int, Any]:
        status, payload, error, _ = _request(client, method, path, json_body=body)
        logs.append({
            "step": f"{method.upper()} {path}",
            "status": status,
            "error": error,
            "response": _shorten(payload),
        })
        return status, payload

    # Health check first.
    call("GET", "/api/v2/health")

    # world
    status, body = call(
        "POST",
        "/api/v2/worlds",
        {
            "name": f"AllApiProbe-World-{uuid.uuid4().hex[:6]}",
            "description": "fixture for all endpoint probe",
            "genre": "mystery",
        },
    )
    if status == 200:
        world_id = _pick_first_id(body, ["id", "world_id"])
        if world_id:
            ctx.world_id = world_id
            ctx.created["world_id"] = world_id

    # lorebook character entry
    if ctx.world_id:
        status, body = call(
            "POST",
            f"/api/v2/worlds/{ctx.world_id}/lorebook/character",
            {
                "name": "Probe Character",
                "personality": "careful",
                "background": "fixture",
                "inventory": [],
                "current_location": "Probe Tower",
            },
        )
        if status == 200:
            entry_id = _pick_first_id(body, ["entry_id", "id"])
            if entry_id:
                ctx.entry_id = entry_id
                ctx.created["entry_id"] = entry_id

    # story
    if ctx.world_id:
        status, body = call(
            "POST",
            "/api/v2/stories",
            {
                "world_id": ctx.world_id,
                "title": f"AllApiProbe-Story-{uuid.uuid4().hex[:6]}",
                "metadata": {"creation_mode": "improv"},
            },
        )
        if status == 200:
            story_id = _pick_first_id(body, ["id", "story_id"])
            if story_id:
                ctx.story_id = story_id
                ctx.created["story_id"] = story_id
                ctx.session_id = f"story-{story_id}-v2"

    # session
    if ctx.session_id and ctx.world_id:
        call(
            "POST",
            "/api/v2/story/session",
            {
                "session_id": ctx.session_id,
                "world_id": ctx.world_id,
            },
        )

    if ctx.session_id:
        call(
            "PUT",
            f"/api/v2/roleplay/story-state/{ctx.session_id}",
            {
                "chapter": "Probe Chapter",
                "objective": "Probe Objective",
                "conflict": "Probe Conflict",
            },
        )

    # persona
    status, body = call(
        "POST",
        "/api/v2/roleplay/personas",
        {
            "name": f"Probe Persona {uuid.uuid4().hex[:4]}",
            "description": "fixture persona",
            "profile": {"tone": "neutral"},
        },
    )
    if status == 200:
        persona_id = _pick_first_id(body, ["persona_id", "id"])
        if persona_id:
            ctx.persona_id = persona_id
            ctx.created["persona_id"] = persona_id

    # optional script design fixture
    if ctx.story_id:
        status, body = call(
            "POST",
            "/api/v2/script-designs",
            {
                "world_id": ctx.world_id,
                "title": "Probe Script Design",
                "summary": "fixture",
            },
        )
        if status in {200, 201}:
            script_design_id = _pick_first_id(body, ["script_design_id", "id"])
            if script_design_id:
                ctx.script_design_id = script_design_id
                ctx.created["script_design_id"] = script_design_id

    # optional segment fixture
    if ctx.story_id:
        status, body = call(
            "POST",
            f"/api/v2/stories/{ctx.story_id}/segments",
            {
                "prompt": "Write a short probe segment.",
                "content": "probe segment",
                "creation_mode": "improv",
            },
        )
        if status in {200, 201}:
            segment_id = _pick_first_id(body, ["segment_id"]) or _pick_latest_segment_id(body)
            if segment_id:
                ctx.segment_id = segment_id
                ctx.created["segment_id"] = segment_id

    return logs


def _cleanup_fixtures(client: httpx.Client, ctx: FixtureContext) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []

    def call(method: str, path: str) -> None:
        status, body, error, _ = _request(client, method, path)
        logs.append({
            "step": f"{method.upper()} {path}",
            "status": status,
            "error": error,
            "response": _shorten(body),
        })

    if ctx.story_id:
        call("DELETE", f"/api/v2/stories/{ctx.story_id}")
    if ctx.persona_id:
        call("DELETE", f"/api/v2/roleplay/personas/{ctx.persona_id}")
    if ctx.world_id:
        call("DELETE", f"/api/v2/worlds/{ctx.world_id}")

    return logs


def _collect_endpoints(openapi: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    endpoints: list[tuple[str, str, dict[str, Any]]] = []
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        return endpoints

    for path in sorted(paths.keys()):
        methods = paths.get(path)
        if not isinstance(methods, dict):
            continue
        for method in HTTP_METHODS:
            operation = methods.get(method)
            if isinstance(operation, dict):
                endpoints.append((method.upper(), path, operation))
    return endpoints


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]

    lines.append(f"# All API Functional Attempt Report ({summary['executed_at'][:10]})")
    lines.append("")
    lines.append("## 1. Scope")
    lines.append("")
    lines.append("- OpenAPI-driven traversal of all routes")
    lines.append("- Dependency-aware fixture preparation before probing")
    lines.append("- Failure policy: only network errors and 5xx count as FAIL")
    lines.append("")
    lines.append("## 2. Summary")
    lines.append("")
    lines.append(f"- base_url: {summary['base_url']}")
    lines.append(f"- openapi_status: {summary['openapi_status']}")
    lines.append(f"- total_endpoints: {summary['total_endpoints']}")
    lines.append(f"- PASS: {summary['pass_count']}")
    lines.append(f"- WARN: {summary['warn_count']}")
    lines.append(f"- SKIP: {summary['skip_count']}")
    lines.append(f"- FAIL: {summary['fail_count']}")
    lines.append(f"- transport_available_endpoints: {summary['available_endpoints']}")
    lines.append("")
    lines.append("## 3. FAIL Details")
    lines.append("")

    fails = [r for r in report["results"] if r.get("outcome") == "FAIL"]
    if not fails:
        lines.append("- No FAIL endpoints.")
    else:
        lines.append("| # | Method | Path | Status | Error |")
        lines.append("| --- | --- | --- | --- | --- |")
        for i, item in enumerate(fails, start=1):
            lines.append(
                f"| {i} | {item['method']} | {item['path']} | {item['status']} | {str(item.get('error') or '-').replace('|', '\\|')} |"
            )

    lines.append("")
    lines.append("## 4. WARN Details")
    lines.append("")
    warns = [r for r in report["results"] if r.get("outcome") == "WARN"]
    if not warns:
        lines.append("- No WARN endpoints.")
    else:
        lines.append("| # | Method | Path | Status | Note |")
        lines.append("| --- | --- | --- | --- | --- |")
        for i, item in enumerate(warns, start=1):
            lines.append(
                f"| {i} | {item['method']} | {item['path']} | {item['status']} | {str(item.get('note') or '-').replace('|', '\\|')} |"
            )

    lines.append("")
    lines.append("## 5. Fixture Lifecycle")
    lines.append("")
    lines.append("### 5.1 Prepare")
    for step in report.get("fixture_prepare", []):
        lines.append(f"- {step['step']} -> {step['status']}")

    lines.append("")
    lines.append("### 5.2 Cleanup")
    for step in report.get("fixture_cleanup", []):
        lines.append(f"- {step['step']} -> {step['status']}")

    lines.append("")
    lines.append("## 6. Outputs")
    lines.append("")
    lines.append(f"- JSON: {REPORT_JSON.as_posix()}")
    lines.append(f"- Markdown: {REPORT_MD.as_posix()}")

    return "\n".join(lines)


def run() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    ctx = FixtureContext()
    endpoint_results: list[EndpointResult] = []

    with httpx.Client(timeout=TIMEOUT) as client:
        openapi_status, openapi_body, openapi_error, _ = _request(client, "GET", "/openapi.json")
        if openapi_error or openapi_status != 200:
            report = {
                "summary": {
                    "base_url": BASE_URL,
                    "openapi_status": openapi_status,
                    "total_endpoints": 0,
                    "pass_count": 0,
                    "warn_count": 0,
                    "skip_count": 0,
                    "fail_count": 1,
                    "available_endpoints": 0,
                    "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "fatal": "openapi_unreachable",
                    "error": openapi_error or openapi_body,
                },
                "fixture_context": asdict(ctx),
                "fixture_prepare": [],
                "fixture_cleanup": [],
                "results": [],
            }
            REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
            return report

        if not isinstance(openapi_body, dict):
            openapi_body = {}

        fixture_prepare_logs = _prepare_fixtures(client, ctx)

        components = ((openapi_body.get("components") or {}).get("schemas") or {}) if isinstance(openapi_body, dict) else {}
        endpoints = _collect_endpoints(openapi_body)

        for method, path, operation in endpoints:
            op_id = operation.get("operationId") if isinstance(operation, dict) else None
            probe_path, cleanup_calls = _prepare_probe_target(client, method, path, ctx)

            query_params = _build_query_params(operation, components, ctx)
            body, body_required = _build_body(method, path, operation, components, ctx)

            # Use stream mode for SSE endpoint.
            stream_mode = method == "POST" and path.endswith("/generate/stream")

            status, response_body, error, duration_ms = _request(
                client,
                method,
                probe_path,
                params=query_params,
                json_body=body,
                stream_mode=stream_mode,
            )

            outcome, available = _classify(status, error)
            note = None
            if outcome == "WARN":
                note = "non-2xx business/validation response, treated as reachable"
            if body_required and body is None:
                note = (note + "; " if note else "") + "request body media type unsupported or unresolved"

            endpoint_results.append(
                EndpointResult(
                    method=method,
                    path=path,
                    probe_url_path=probe_path,
                    operation_id=op_id,
                    status=status,
                    outcome=outcome,
                    available=available,
                    duration_ms=duration_ms,
                    body_required=body_required,
                    query_params_used=query_params,
                    request_body_preview=_shorten(body),
                    response_preview=_shorten(response_body),
                    note=note,
                    error=error,
                )
            )

            for cleanup_method, cleanup_path in cleanup_calls:
                _request(client, cleanup_method, cleanup_path)

        fixture_cleanup_logs = _cleanup_fixtures(client, ctx)

    pass_count = sum(1 for item in endpoint_results if item.outcome == "PASS")
    warn_count = sum(1 for item in endpoint_results if item.outcome == "WARN")
    skip_count = sum(1 for item in endpoint_results if item.outcome == "SKIP")
    fail_count = sum(1 for item in endpoint_results if item.outcome == "FAIL")

    report = {
        "summary": {
            "base_url": BASE_URL,
            "openapi_status": openapi_status,
            "total_endpoints": len(endpoint_results),
            "pass_count": pass_count,
            "warn_count": warn_count,
            "skip_count": skip_count,
            "fail_count": fail_count,
            "available_endpoints": len(endpoint_results) - fail_count,
            "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "policy": {
                "PASS": "2xx",
                "WARN": "non-2xx and non-5xx reachable responses",
                "FAIL": "network errors and 5xx",
            },
        },
        "fixture_context": asdict(ctx),
        "fixture_prepare": fixture_prepare_logs,
        "fixture_cleanup": fixture_cleanup_logs,
        "results": [asdict(item) for item in endpoint_results],
    }

    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
    return report


def main() -> None:
    report = run()
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON report: {REPORT_JSON}")
    print(f"MD report: {REPORT_MD}")


if __name__ == "__main__":
    main()
