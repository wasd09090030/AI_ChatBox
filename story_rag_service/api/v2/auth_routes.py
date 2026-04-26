"""登录认证相关路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.dependencies.auth import get_auth_service, get_current_user
from config import settings
from models.auth import (
    AuthSessionResponse,
    AuthenticatedUserResponse,
    LegacyClaimRequest,
    LegacyClaimResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from models.user import User
from services.auth_service import AuthService

router = APIRouter()


def _to_authenticated_user_response(user: User) -> AuthenticatedUserResponse:
    """将内部 User 模型映射为前端可读结构。"""
    return AuthenticatedUserResponse(
        user_id=user.id,
        login_identifier=user.login_identifier or "",
        display_name=user.display_name or user.login_identifier or user.id,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _set_auth_cookie(response: Response, session_token: str) -> None:
    """统一写入登录 Cookie。"""
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_session_ttl_hours * 3600,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """统一清理登录 Cookie。"""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


@router.post("/auth/register", response_model=AuthSessionResponse)
async def register(
    payload: RegisterRequest,
    http_request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """注册账号并直接创建登录会话。"""
    try:
        user = auth_service.register_user(
            login_identifier=payload.login_identifier,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_token = auth_service.create_session(
        user_id=user.id,
        created_ip=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent"),
    )
    _set_auth_cookie(response, session_token)
    return AuthSessionResponse(user=_to_authenticated_user_response(user))


@router.post("/auth/login", response_model=AuthSessionResponse)
async def login(
    payload: LoginRequest,
    http_request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """登录并创建浏览器会话。"""
    try:
        user = auth_service.authenticate_user(
            login_identifier=payload.login_identifier,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    session_token = auth_service.create_session(
        user_id=user.id,
        created_ip=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent"),
    )
    user = auth_service.user_manager.get_user(user.id) or user
    _set_auth_cookie(response, session_token)
    return AuthSessionResponse(user=_to_authenticated_user_response(user))


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """注销当前浏览器会话。"""
    session_token = request.cookies.get(settings.auth_cookie_name) or ""
    if session_token:
        auth_service.revoke_session(session_token)
    _clear_auth_cookie(response)
    return LogoutResponse(success=True)


@router.get("/auth/me", response_model=AuthenticatedUserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """返回当前登录用户。"""
    return _to_authenticated_user_response(current_user)


@router.post("/auth/claim-legacy", response_model=LegacyClaimResponse)
async def claim_legacy_identity(
    payload: LegacyClaimRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """将旧匿名 ID 上可明确归属的数据迁移到当前账号。"""
    result = auth_service.claim_legacy_user_data(
        current_user_id=current_user.id,
        legacy_user_id=payload.legacy_user_id,
        claim_unowned_data=payload.claim_unowned_data,
    )
    return LegacyClaimResponse(**result)
