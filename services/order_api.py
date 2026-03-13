"""HTTP-like API client wrappers for order domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_orders_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/orders")
    return list(data) if isinstance(data, list) else []


def refund_order(
    *,
    order_id: int,
    reason: str,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        f"/api/v1/orders/{int(order_id)}/refund",
        {
            "reason": reason,
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def get_order_snapshot(
    order_id: int,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", f"/api/v1/orders/{int(order_id)}")
    return dict(data) if isinstance(data, dict) else {}


def refresh_order_status(
    order_id: int,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("POST", f"/api/v1/orders/{int(order_id)}/refresh-status")
    return dict(data) if isinstance(data, dict) else {}
