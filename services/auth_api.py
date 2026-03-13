"""HTTP-like API client wrappers for auth domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def authenticate_admin(
    username: str,
    password: str,
    *,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/auth/login",
        {
            "username": str(username or ""),
            "password": str(password or ""),
        },
    )
    if not isinstance(data, dict) or not data:
        return None
    return dict(data)


def get_auth_me(
    username: str = "",
    *,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json(
        "GET",
        "/api/v1/auth/me",
        {"username": str(username or "").strip()},
    )
    if not isinstance(data, dict) or not data:
        return None
    return dict(data)


def logout_admin(
    username: str = "",
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/auth/logout",
        {"username": str(username or "").strip()},
    )
    if not isinstance(data, dict):
        return {"ok": False, "username": str(username or "").strip()}
    return dict(data)


def refresh_admin_session(
    username: str = "",
    *,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/auth/refresh",
        {"username": str(username or "").strip()},
    )
    if not isinstance(data, dict) or not data:
        return None
    return dict(data)
