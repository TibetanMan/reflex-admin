"""HTTP API client wrappers for settings domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def get_settings_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", "/api/v1/settings")
    return dict(data) if isinstance(data, dict) else {}


def update_default_usdt_address(
    *,
    address: str,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PUT",
        "/api/v1/settings/default-usdt-address",
        {
            "address": address,
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_usdt_query_api_settings(
    *,
    api_url: str,
    api_key: str,
    timeout_seconds: int,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PUT",
        "/api/v1/settings/usdt-query-api",
        {
            "api_url": api_url,
            "api_key": api_key,
            "timeout_seconds": int(timeout_seconds),
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_bins_query_api_settings(
    *,
    api_url: str,
    api_key: str,
    timeout_seconds: int,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PUT",
        "/api/v1/settings/bins-query-api",
        {
            "api_url": api_url,
            "api_key": api_key,
            "timeout_seconds": int(timeout_seconds),
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_telegram_push_settings(
    *,
    enabled: bool,
    bot_token: str,
    chat_id: str,
    push_interval_seconds: int,
    max_messages_per_minute: int,
    retry_times: int,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PUT",
        "/api/v1/settings/telegram-push",
        {
            "enabled": bool(enabled),
            "bot_token": bot_token,
            "chat_id": chat_id,
            "push_interval_seconds": int(push_interval_seconds),
            "max_messages_per_minute": int(max_messages_per_minute),
            "retry_times": int(retry_times),
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}
