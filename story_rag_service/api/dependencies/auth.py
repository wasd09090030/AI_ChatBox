"""认证依赖提供器。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from api.service_context import get_container
from config import settings
from models.user import User
from repositories.auth_session_repository import SqliteAuthSessionRepository
from services.auth_service import AuthService


def get_auth_service() -> AuthService:
    """返回认证服务。"""
    try:
        user_manager = get_container().user_manager_ref
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=503, detail="Auth service is not ready") from exc

    if user_manager is None:
        raise HTTPException(status_code=503, detail="Auth service is not ready")

    return AuthService(
        user_manager=user_manager,
        session_repository=SqliteAuthSessionRepository(settings.database_path),
    )


def get_optional_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    """尝试解析当前登录用户，未登录时返回 None。"""
    session_token = request.cookies.get(settings.auth_cookie_name) or ""
    return auth_service.get_user_from_session_token(session_token)


def get_current_user(current_user: User | None = Depends(get_optional_current_user)) -> User:
    """要求当前请求必须已登录。"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user
