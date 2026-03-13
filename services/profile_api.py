"""HTTP API client wrappers for profile domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def get_profile_snapshot(
    *,
    username: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "GET",
        "/api/v1/profile",
        {"username": username},
    )
    return dict(data) if isinstance(data, dict) else {}


def update_profile_snapshot(
    *,
    username: str,
    display_name: str,
    email: str,
    phone: str,
    avatar_url: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        "/api/v1/profile",
        {
            "username": username,
            "display_name": display_name,
            "email": email,
            "phone": phone,
            "avatar_url": avatar_url,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_profile_password(
    *,
    username: str,
    old_password: str,
    new_password: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        "/api/v1/profile/password",
        {
            "username": username,
            "old_password": old_password,
            "new_password": new_password,
        },
    )
    return dict(data) if isinstance(data, dict) else {}
