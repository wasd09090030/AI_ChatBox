"""
Smoke API test for console restructuring and scene-based model selection.

Usage:
  python scripts/smoke_console_scene_models.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_USER_ID=smoke-console-user
  SMOKE_PROVIDER=deepseek
  SMOKE_MODEL=deepseek-chat
  RUN_LLM_SMOKE=true
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

# 统一服务地址，允许通过环境变量切换到远端或本地实例。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# 为控制台相关 API 统一附带用户头，便于隔离配置与偏好读取。
USER_ID = os.getenv("SMOKE_USER_ID", "smoke-console-user")
# 目标提供商名称，用于验证默认模型与场景模型配置链路。
TARGET_PROVIDER = os.getenv("SMOKE_PROVIDER", "deepseek").strip().lower()
# 目标模型名称，用于验证控制台配置后的读写一致性。
TARGET_MODEL = os.getenv("SMOKE_MODEL", "deepseek-chat").strip()
# 控制是否执行依赖模型推理的场景链路冒烟测试。
RUN_LLM_SMOKE = os.getenv("RUN_LLM_SMOKE", "true").lower() == "true"
# 为 HTTP 请求设置统一超时时间，避免脚本无限阻塞。
TIMEOUT = 90.0


@dataclass
class StepResult:
    """作用：定义 StepResult 数据结构，用于约束字段语义与序列化格式。"""
    name: str
    passed: bool
    detail: str


def _headers() -> dict[str, str]:
    """为请求附带控制台用户标识，命中用户级配置读取路径。"""
    return {"X-User-ID": USER_ID}


def _assert(cond: bool, message: str) -> None:
    """统一断言行为，失败时抛出可读错误信息。"""
    if not cond:
        raise AssertionError(message)


def _expect_status(resp: httpx.Response, status: int, name: str) -> None:
    """校验响应状态码并在失败时保留调用名与响应片段。"""
    if resp.status_code != status:
        raise AssertionError(
            f"{name} failed: expected {status}, got {resp.status_code}, body={resp.text[:500]}"
        )


def run_smoke() -> list[StepResult]:
    """串行验证控制台改版涉及的 provider、统计与生成链路。"""
    results: list[StepResult] = []
    with httpx.Client(timeout=TIMEOUT) as client:
        # 1) basic health + provider status
        r = client.get(f"{BASE_URL}/api/v2/health")
        _expect_status(r, 200, "GET /api/v2/health")
        results.append(StepResult("health", True, r.text.strip()))

        r = client.get(f"{BASE_URL}/api/v2/providers", headers=_headers())
        _expect_status(r, 200, "GET /api/v2/providers")
        provider_items = r.json().get("providers", [])
        providers = {
            item.get("provider"): item
            for item in provider_items
            if isinstance(item, dict) and item.get("provider")
        }
        _assert(TARGET_PROVIDER in providers, f"provider '{TARGET_PROVIDER}' not found")
        results.append(
            StepResult(
                "providers",
                True,
                f"{TARGET_PROVIDER} available={providers[TARGET_PROVIDER].get('available')}",
            )
        )

        # 2) default provider/model selection
        payload_default = {"provider": TARGET_PROVIDER, "model": TARGET_MODEL}
        r = client.put(
            f"{BASE_URL}/api/v2/providers/default-selection",
            json=payload_default,
            headers=_headers(),
        )
        _expect_status(r, 200, "PUT /api/v2/providers/default-selection")
        body = r.json()
        _assert(body.get("provider") == TARGET_PROVIDER, "default provider not saved")
        _assert(body.get("model") == TARGET_MODEL, "default model not saved")
        results.append(StepResult("default-selection-put", True, str(body)))

        r = client.get(f"{BASE_URL}/api/v2/providers/default-selection", headers=_headers())
        _expect_status(r, 200, "GET /api/v2/providers/default-selection")
        body = r.json()
        _assert(body.get("provider") == TARGET_PROVIDER, "default provider mismatch")
        _assert(body.get("model") == TARGET_MODEL, "default model mismatch")
        results.append(StepResult("default-selection-get", True, str(body)))

        # 3) scene model preferences
        scene_payload = {
            "story_generation": {"provider": TARGET_PROVIDER, "model": TARGET_MODEL},
            "input_enhancement": {"provider": TARGET_PROVIDER, "model": TARGET_MODEL},
            "story_adjustment": {"provider": TARGET_PROVIDER, "model": TARGET_MODEL},
        }
        r = client.put(
            f"{BASE_URL}/api/v2/providers/scene-models",
            json=scene_payload,
            headers=_headers(),
        )
        _expect_status(r, 200, "PUT /api/v2/providers/scene-models")
        body = r.json()
        for scene in ("story_generation", "input_enhancement", "story_adjustment"):
            _assert(body[scene]["provider"] == TARGET_PROVIDER, f"{scene}.provider mismatch")
            _assert(body[scene]["model"] == TARGET_MODEL, f"{scene}.model mismatch")
        results.append(StepResult("scene-models-put", True, "all three scenes saved"))

        r = client.get(f"{BASE_URL}/api/v2/providers/scene-models", headers=_headers())
        _expect_status(r, 200, "GET /api/v2/providers/scene-models")
        body = r.json()
        _assert("fallback" in body, "fallback not returned")
        results.append(StepResult("scene-models-get", True, str(body)))

        # 4) analytics endpoints used by console pages
        r = client.get(f"{BASE_URL}/api/v2/stats/overview")
        _expect_status(r, 200, "GET /api/v2/stats/overview")
        overview = r.json()
        _assert("total_requests" in overview, "overview.total_requests missing")
        _assert("total_tokens" in overview, "overview.total_tokens missing")
        results.append(
            StepResult(
                "stats-overview",
                True,
                f"total_requests={overview.get('total_requests')}, success_rate={overview.get('success_rate')}",
            )
        )

        r = client.get(f"{BASE_URL}/api/v2/stats/daily", params={"days": 7})
        _expect_status(r, 200, "GET /api/v2/stats/daily")
        daily = r.json()
        if isinstance(daily, list):
            daily_items = daily
        elif isinstance(daily, dict):
            if isinstance(daily.get("items"), list):
                daily_items = daily.get("items", [])
            elif isinstance(daily.get("value"), list):
                daily_items = daily.get("value", [])
            else:
                daily_items = []
        else:
            daily_items = []
        _assert(isinstance(daily_items, list) and len(daily_items) > 0, "daily items missing")
        results.append(StepResult("stats-daily", True, f"items={len(daily_items)}"))

        r = client.get(f"{BASE_URL}/api/v2/stats/log", params={"limit": 10})
        _expect_status(r, 200, "GET /api/v2/stats/log")
        log_body = r.json()
        _assert(isinstance(log_body.get("events"), list), "stats log events missing")
        results.append(StepResult("stats-log", True, f"events={len(log_body.get('events', []))}"))

        r = client.get(f"{BASE_URL}/api/v2/stats/filter-options")
        _expect_status(r, 200, "GET /api/v2/stats/filter-options")
        filter_options = r.json()
        _assert("models" in filter_options, "filter-options models missing")
        results.append(StepResult("stats-filter-options", True, str({k: len(v) if isinstance(v, list) else v for k, v in filter_options.items()})))

        if not RUN_LLM_SMOKE:
            results.append(StepResult("llm-chain", True, "skipped by RUN_LLM_SMOKE=false"))
            return results

        # 5) story generation chain
        r = client.post(f"{BASE_URL}/api/v2/story/session", json={})
        _expect_status(r, 200, "POST /api/v2/story/session")
        session_id = r.json()["session_id"]

        generate_payload = {
            "session_id": session_id,
            "user_input": "请写一句冒烟测试开场。",
            "use_rag": False,
            "temperature": 0.7,
            # 故意省略 provider/model，用于验证默认选择路径可用
        }
        r = client.post(
            f"{BASE_URL}/api/v2/story/generate",
            json=generate_payload,
            headers=_headers(),
        )
        _expect_status(r, 200, "POST /api/v2/story/generate")
        generate_body = r.json()
        _assert(len((generate_body.get("output_text") or "").strip()) > 0, "generate output empty")
        _assert(TARGET_PROVIDER in (generate_body.get("model") or "").lower(), "generate model does not look like deepseek")
        results.append(
            StepResult(
                "story-generate",
                True,
                f"session_id={session_id}, model={generate_body.get('model')}, len={len(generate_body.get('output_text', ''))}",
            )
        )

        # 6) input enhancement chain
        preview_payload = {
            "session_id": session_id,
            "user_input": "他很紧张",
            "temperature": 0.7,
            # 故意省略 provider/model，用于验证兜底路径可用
        }
        r = client.post(
            f"{BASE_URL}/api/v2/story/input-enhancement/preview",
            json=preview_payload,
            headers=_headers(),
        )
        _expect_status(r, 200, "POST /api/v2/story/input-enhancement/preview")
        preview_body = r.json()
        _assert("enhanced_text" in preview_body, "preview enhanced_text missing")
        results.append(
            StepResult(
                "input-enhancement-preview",
                True,
                f"applied={preview_body.get('applied')}, original={preview_body.get('original_text')}, enhanced={preview_body.get('enhanced_text')}",
            )
        )

        # 7) story adjustment chain
        world_payload = {
            "name": f"SmokeWorld-{uuid.uuid4().hex[:6]}",
            "description": "Smoke world for scene model validation",
            "genre": "fantasy",
        }
        r = client.post(f"{BASE_URL}/api/v2/worlds", json=world_payload)
        _expect_status(r, 200, "POST /api/v2/worlds")
        world_id = r.json()["id"]

        r = client.post(
            f"{BASE_URL}/api/v2/stories",
            json={"world_id": world_id, "title": "Smoke Story"},
        )
        _expect_status(r, 200, "POST /api/v2/stories")
        story = r.json()
        story_id = story["id"]

        r = client.post(
            f"{BASE_URL}/api/v2/stories/{story_id}/segments",
            json={
                "prompt": "打开阁楼",
                "content": "主角推开阁楼门，看见一封破旧的信。",
                "retrieved_context": [],
            },
        )
        _expect_status(r, 200, "POST /api/v2/stories/{story_id}/segments")
        story = r.json()
        segment_id = story["segments"][0]["id"]

        scene_prefs = body
        adjustment_pref = scene_prefs.get("story_adjustment", {})
        polish_payload = {
            "story_id": story_id,
            "session_id": f"smoke-adjust-{uuid.uuid4().hex[:8]}",
            "segment_id": segment_id,
            "selected_text": "一封破旧的信",
            "preset_key": "style_refine",
            "preset_instruction": "在不改变事实的前提下更有画面感",
            "custom_instruction": "保持悬疑语气",
            "provider": adjustment_pref.get("provider") or TARGET_PROVIDER,
            "model": adjustment_pref.get("model") or TARGET_MODEL,
            "temperature": 0.7,
        }
        r = client.post(
            f"{BASE_URL}/api/v2/story/adjustments/polish",
            json=polish_payload,
            headers=_headers(),
        )
        _expect_status(r, 200, "POST /api/v2/story/adjustments/polish")
        polish_body = r.json()
        _assert(len((polish_body.get("polished_text") or "").strip()) > 0, "polished_text empty")
        _assert(TARGET_PROVIDER in (polish_body.get("model") or "").lower(), "polish model does not look like deepseek")
        results.append(
            StepResult(
                "story-adjustment-polish",
                True,
                f"story_id={story_id}, segment_id={segment_id}, model={polish_body.get('model')}",
            )
        )

    return results


def main() -> None:
    """执行控制台场景模型冒烟并打印逐步结果摘要。"""
    print(
        f"[SMOKE-CONSOLE] base_url={BASE_URL} user_id={USER_ID} provider={TARGET_PROVIDER} model={TARGET_MODEL} llm={RUN_LLM_SMOKE}"
    )
    results = run_smoke()
    passed = sum(1 for item in results if item.passed)
    total = len(results)

    for item in results:
        status = "OK" if item.passed else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    print(f"[DONE] console/scene-model smoke passed {passed}/{total}")


if __name__ == "__main__":
    main()
