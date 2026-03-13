"""HTTP API client wrappers for admin account lifecycle."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def create_admin_account(
    *,
    actor_username: str,
    username: str,
    display_name: str,
    role: str,
    email: str = "",
    initial_password: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/admin/accounts",
        {
            "actor_username": actor_username,
            "username": username,
            "display_name": display_name,
            "role": role,
            "email": email,
            "initial_password": initial_password,
        },
    )
    return dict(data) if isinstance(data, dict) else {}
