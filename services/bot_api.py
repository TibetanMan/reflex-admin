"""HTTP-like API client wrappers for bot domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_bot_owner_options(
    *,
    session_factory: Optional[Any] = None,
) -> list[str]:
    del session_factory
    data = request_json("GET", "/api/v1/bots/owner-options")
    return list(data) if isinstance(data, list) else []


def list_bots_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/bots")
    return list(data) if isinstance(data, list) else []


def create_bot_record(
    *,
    name: str,
    token: str,
    owner_name: str,
    usdt_address: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/bots",
        {
            "name": name,
            "token": token,
            "owner_name": owner_name,
            "usdt_address": usdt_address,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_bot_record(
    *,
    bot_id: int,
    name: str,
    owner_name: str,
    usdt_address: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/bots/{int(bot_id)}",
        {
            "name": name,
            "owner_name": owner_name,
            "usdt_address": usdt_address,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def delete_bot_record(
    *,
    bot_id: int,
    session_factory: Optional[Any] = None,
) -> None:
    del session_factory
    request_json("DELETE", f"/api/v1/bots/{int(bot_id)}")


def toggle_bot_record_status(
    *,
    bot_id: int,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/bots/{int(bot_id)}/status",
    )
    return dict(data) if isinstance(data, dict) else {}
