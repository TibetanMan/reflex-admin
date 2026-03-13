"""HTTP-like API client wrappers for dashboard domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def get_dashboard_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", "/api/v1/dashboard/summary")
    return dict(data) if isinstance(data, dict) else {}


def _request_list(path: str, limit: int) -> list[dict[str, Any]]:
    data = request_json("GET", path, {"limit": int(limit)})
    if not isinstance(data, list):
        return []
    return [dict(item) for item in data if isinstance(item, dict)]


def list_recent_orders(
    limit: int = 10,
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    return _request_list("/api/v1/dashboard/recent-orders", limit=limit)


def list_recent_deposits(
    limit: int = 10,
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    return _request_list("/api/v1/dashboard/recent-deposits", limit=limit)


def list_top_categories(
    limit: int = 10,
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    return _request_list("/api/v1/dashboard/top-categories", limit=limit)


def list_bot_status(
    limit: int = 10,
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    return _request_list("/api/v1/dashboard/bot-status", limit=limit)
