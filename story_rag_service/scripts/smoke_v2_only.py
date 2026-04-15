"""
V2-only smoke test script for Story RAG Service.

Usage:
  python scripts/smoke_v2_only.py

Optional env:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  RUN_LLM_SMOKE=true
"""

from __future__ import annotations

import os
import uuid

import httpx

# 统一服务地址，允许通过环境变量切换到远端或本地实例。
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# 控制是否执行依赖模型推理的冒烟用例。
RUN_LLM_SMOKE = os.getenv("RUN_LLM_SMOKE", "true").lower() == "true"
# 为 HTTP 请求设置统一超时时间，避免脚本无限阻塞。
TIMEOUT = 30.0


def main() -> None:
    """执行 v2 基础可用性检查，并按配置决定是否验证生成接口。"""
    print(f"[SMOKE-V2] base_url={BASE_URL}")

    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{BASE_URL}/docs")
        assert response.status_code == 200, f"/docs failed: {response.status_code}, {response.text}"
        print("[OK] /docs")

        response = client.get(f"{BASE_URL}/api/v2/health")
        assert response.status_code == 200, f"/api/v2/health failed: {response.status_code}, {response.text}"
        print("[OK] /api/v2/health")

        session_response = client.post(f"{BASE_URL}/api/v2/story/session", json={})
        assert (
            session_response.status_code == 200
        ), f"POST /api/v2/story/session failed: {session_response.status_code}, {session_response.text}"
        session_id = session_response.json()["session_id"]
        print(f"[OK] /api/v2/story/session -> {session_id}")

        session_info = client.get(f"{BASE_URL}/api/v2/story/session/{session_id}")
        assert (
            session_info.status_code == 200
        ), f"GET /api/v2/story/session/{{session_id}} failed: {session_info.status_code}, {session_info.text}"
        print(f"[OK] /api/v2/story/session/{session_id}")

        if RUN_LLM_SMOKE:
            response = client.post(
                f"{BASE_URL}/api/v2/story/generate",
                json={
                    "session_id": f"smoke_session_v2_{uuid.uuid4().hex[:8]}",
                    "user_input": "请写一句简短开场。",
                    "use_rag": False,
                    "temperature": 0.7,
                },
            )
            assert response.status_code == 200, f"v2 generate failed: {response.status_code}, {response.text}"
            print("[OK] /api/v2/story/generate")
        else:
            print("[SKIP] v2 generation smoke (set RUN_LLM_SMOKE=true)")

    print("[DONE] V2-only smoke checks passed")


if __name__ == "__main__":
    main()
