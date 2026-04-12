"""
Provider configuration, model listing, and connectivity routes for story generation.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Query

from api.service_context import get_container
from models.user import UserSettingsUpdate
from services.ai_proxy_service import AIProxyService, PROVIDER_REGISTRY, _resolve_base_url

from .provider_schemas import (
    DefaultProviderSelection,
    ProviderConfigUpdate,
    SceneModelPreferencesResponse,
    SceneModelPreferencesUpdate,
    TestConnectionRequest,
)

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)
# 变量作用：FastAPI 路由注册器，用于挂载本模块接口。
router = APIRouter()


def _get_user_manager():
    """获取用户管理器实例，不可用时返回 503。"""
    try:
        user_manager = get_container().user_manager_ref
    except Exception as exc:
        logger.error("provider routes unavailable: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Provider service is not ready") from exc

    if user_manager is None:
        raise HTTPException(status_code=503, detail="Provider service is not ready")

    return user_manager


@router.get("/providers")
async def get_available_providers(user_id: str = Header(..., alias="X-User-ID")):
    """获取当前用户可用的提供商列表及可用状态。"""
    try:
        proxy = AIProxyService(_get_user_manager())
        return {"providers": proxy.get_providers_info(user_id)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get available providers: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/providers/config")
async def update_provider_config(
    update: ProviderConfigUpdate,
    user_id: str = Header(..., alias="X-User-ID"),
):
    """更新提供商配置（API Key 与自定义 Base URL）。"""
    try:
        user_manager = _get_user_manager()
        user_manager.get_or_create_user(user_id)

        if update.api_key is not None:
            if update.api_key.strip():
                user_manager.update_api_key(user_id, update.provider, update.api_key.strip())
            else:
                user_manager.delete_api_key(user_id, update.provider)

        if update.base_url is not None:
            user_manager.update_base_url(user_id, update.provider, update.base_url.strip())

        return {"success": True, "provider": update.provider}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to update provider config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/providers/test-connection")
async def test_provider_connection(
    request: TestConnectionRequest,
    user_id: str = Header(..., alias="X-User-ID"),
):
    """使用用户配置探测提供商连接可用性。"""
    user_manager = _get_user_manager()
    proxy = AIProxyService(user_manager)

    api_key = user_manager.get_decrypted_api_key(user_id, request.provider)
    if not api_key:
        return {
            "success": False,
            "status": "no_key",
            "message": f"未找到 {request.provider} 的 API Key，请先在设置中保存",
        }

    cfg = PROVIDER_REGISTRY.get(request.provider)
    if not cfg:
        return {
            "success": False,
            "status": "unknown",
            "message": f"未知提供商: {request.provider}",
        }

    user_base_url = proxy.user_manager.get_base_url(user_id, request.provider)
    try:
        base_url = _resolve_base_url(cfg, user_base_url, request.base_url)
    except ValueError as exc:
        return {"success": False, "status": "no_base_url", "message": str(exc)}

    if cfg.protocol == "anthropic":
        url = f"{base_url}/v1/models"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    else:
        versioned = (
            base_url
            if "/v" in base_url.split("/")[-1] or base_url.endswith("/v1")
            else f"{base_url}/v1"
        )
        url = f"{versioned}/models"
        headers = {"Authorization": f"Bearer {api_key}"}

    started_at = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
        latency_ms = round((time.perf_counter() - started_at) * 1000)

        if response.status_code == 200:
            return {
                "success": True,
                "status": "ok",
                "message": f"连接成功，响应时间 {latency_ms}ms",
                "latency_ms": latency_ms,
            }

        try:
            body = response.json()
            detail = (
                body.get("error", {}).get("message")
                or body.get("message")
                or body.get("detail")
                or str(body)
            )
        except Exception:
            detail = response.text[:200]

        if response.status_code in (401, 403):
            return {
                "success": False,
                "status": "unauthorized",
                "message": f"API Key 无效或权限不足（HTTP {response.status_code}）：{detail}",
                "latency_ms": latency_ms,
            }
        if response.status_code == 404:
            return {
                "success": False,
                "status": "not_found",
                "message": f"端点未找到（HTTP 404），请确认 Base URL：{detail}",
                "latency_ms": latency_ms,
            }
        return {
            "success": False,
            "status": "unknown",
            "message": f"服务端返回错误（HTTP {response.status_code}）：{detail}",
            "latency_ms": latency_ms,
        }
    except httpx.TimeoutException:
        return {"success": False, "status": "timeout", "message": "请求超时，请检查 Base URL 是否可达"}
    except Exception as exc:
        logger.error("test_provider_connection error: %s", exc, exc_info=True)
        return {"success": False, "status": "network_error", "message": f"网络错误：{exc}"}


@router.get("/providers/default-selection", response_model=DefaultProviderSelection)
async def get_default_provider_selection(user_id: str = Header(..., alias="X-User-ID")):
    """获取用户全局默认 provider/model 选择。"""
    try:
        user_manager = _get_user_manager()
        return DefaultProviderSelection(**user_manager.get_default_provider_selection(user_id))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get default provider selection: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/providers/default-selection", response_model=DefaultProviderSelection)
async def update_default_provider_selection(
    update: DefaultProviderSelection,
    user_id: str = Header(..., alias="X-User-ID"),
):
    """保存用户全局默认 provider/model 选择。"""
    try:
        user_manager = _get_user_manager()
        user = user_manager.update_user_settings(
            user_id,
            UserSettingsUpdate(
                default_provider=update.provider,
                default_model=update.model.strip(),
            ),
        )
        return DefaultProviderSelection(
            provider=user.settings.default_provider,
            model=user.settings.default_model,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to update default provider selection: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/providers/scene-models", response_model=SceneModelPreferencesResponse)
async def get_scene_model_preferences(user_id: str = Header(..., alias="X-User-ID")):
    """获取用户分场景模型偏好配置。"""
    try:
        user_manager = _get_user_manager()
        user = user_manager.get_or_create_user(user_id)
        preferences = user_manager.get_scene_model_preferences(user_id)
        preferences["fallback"] = {
            "default_provider": user.settings.default_provider,
            "default_model": user.settings.default_model,
        }
        return preferences
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get scene model preferences: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/providers/scene-models", response_model=SceneModelPreferencesResponse)
async def update_scene_model_preferences(
    update: SceneModelPreferencesUpdate,
    user_id: str = Header(..., alias="X-User-ID"),
):
    """更新用户分场景模型偏好配置。"""
    try:
        user_manager = _get_user_manager()
        user = user_manager.update_scene_model_preferences(
            user_id,
            {
                "story_generation": update.story_generation.model_dump(),
                "input_enhancement": update.input_enhancement.model_dump(),
                "story_adjustment": update.story_adjustment.model_dump(),
            },
        )
        preferences = user_manager.get_scene_model_preferences(user_id)
        preferences["fallback"] = {
            "default_provider": user.settings.default_provider,
            "default_model": user.settings.default_model,
        }
        return preferences
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to update scene model preferences: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    user_id: str = Header(..., alias="X-User-ID"),
    base_url: Optional[str] = Query(None, description="覆盖默认 Base URL"),
):
    """拉取提供商模型列表，失败时回退预置模型。"""
    user_manager = _get_user_manager()

    api_key = user_manager.get_decrypted_api_key(user_id, provider)
    if not api_key:
        raise HTTPException(status_code=400, detail=f"未找到 {provider} 的 API Key")

    cfg = PROVIDER_REGISTRY.get(provider)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"未知提供商: {provider}")

    user_base_url = user_manager.get_base_url(user_id, provider)
    try:
        resolved = _resolve_base_url(cfg, user_base_url, base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if cfg.protocol == "anthropic":
        url = f"{resolved}/v1/models"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    else:
        versioned = (
            resolved
            if "/v" in resolved.split("/")[-1] or resolved.endswith("/v1")
            else f"{resolved}/v1"
        )
        url = f"{versioned}/models"
        headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            logger.warning("list_provider_models remote %s -> %s，回退预置模型", url, response.status_code)
            return {"source": "preset", "models": [{"id": model_id} for model_id in cfg.models]}

        body = response.json()
        raw_models = body.get("data") or body.get("models") or (body if isinstance(body, list) else [])
        models = sorted(
            [
                {"id": str(item.get("id", item) if isinstance(item, dict) else item)}
                for item in raw_models
            ],
            key=lambda item: item["id"],
        )
        return {"source": "remote", "models": models}
    except Exception as exc:
        logger.warning("list_provider_models 失败（%s），回退预置模型：%s", provider, exc)
        return {"source": "preset", "models": [{"id": model_id} for model_id in cfg.models]}
