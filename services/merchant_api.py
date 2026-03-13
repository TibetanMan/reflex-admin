"""HTTP-like API client wrappers for merchant domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_merchants_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/merchants")
    return list(data) if isinstance(data, list) else []


def create_merchant_record(
    *,
    name: str,
    description: str,
    contact_telegram: str,
    contact_email: str,
    fee_rate: float,
    usdt_address: str,
    is_featured: bool,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/merchants",
        {
            "name": name,
            "description": description,
            "contact_telegram": contact_telegram,
            "contact_email": contact_email,
            "fee_rate": float(fee_rate),
            "usdt_address": usdt_address,
            "is_featured": bool(is_featured),
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_merchant_record(
    *,
    merchant_id: int,
    name: str,
    description: str,
    contact_telegram: str,
    contact_email: str,
    fee_rate: float,
    usdt_address: str,
    is_verified: bool,
    is_featured: bool,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/merchants/{int(merchant_id)}",
        {
            "name": name,
            "description": description,
            "contact_telegram": contact_telegram,
            "contact_email": contact_email,
            "fee_rate": float(fee_rate),
            "usdt_address": usdt_address,
            "is_verified": bool(is_verified),
            "is_featured": bool(is_featured),
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def toggle_merchant_status(
    *,
    merchant_id: int,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("PATCH", f"/api/v1/merchants/{int(merchant_id)}/status")
    return dict(data) if isinstance(data, dict) else {}


def toggle_merchant_featured(
    *,
    merchant_id: int,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("PATCH", f"/api/v1/merchants/{int(merchant_id)}/featured")
    return dict(data) if isinstance(data, dict) else {}


def toggle_merchant_verified(
    *,
    merchant_id: int,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("PATCH", f"/api/v1/merchants/{int(merchant_id)}/verified")
    return dict(data) if isinstance(data, dict) else {}
