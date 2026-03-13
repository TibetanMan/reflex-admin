"""HTTP API client wrappers for inventory domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_inventory_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/inventory/libraries")
    return list(data) if isinstance(data, list) else []


def list_inventory_filter_options(
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, list[str]]:
    del session_factory
    data = request_json("GET", "/api/v1/inventory/options")
    return dict(data) if isinstance(data, dict) else {"merchant_names": [], "category_names": []}


def import_inventory_library(
    *,
    name: str,
    merchant_name: str,
    category_name: str,
    unit_price: float,
    pick_price: float,
    delimiter: str,
    content: str,
    push_ad: bool,
    operator_username: str,
    source_filename: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/inventory/libraries/import",
        {
            "name": name,
            "merchant_name": merchant_name,
            "category_name": category_name,
            "unit_price": float(unit_price),
            "pick_price": float(pick_price),
            "delimiter": delimiter,
            "content": content,
            "push_ad": bool(push_ad),
            "operator_username": operator_username,
            "source_filename": source_filename,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_inventory_price(
    *,
    inventory_id: int,
    unit_price: float,
    pick_price: float,
    operator_username: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/inventory/libraries/{int(inventory_id)}/price",
        {
            "unit_price": float(unit_price),
            "pick_price": float(pick_price),
            "operator_username": str(operator_username or "").strip(),
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def toggle_inventory_status(
    *,
    inventory_id: int,
    operator_username: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/inventory/libraries/{int(inventory_id)}/status",
        {"operator_username": str(operator_username or "").strip()},
    )
    return dict(data) if isinstance(data, dict) else {}


def delete_inventory_library(
    *,
    inventory_id: int,
    operator_username: str = "",
    session_factory: Optional[Any] = None,
) -> None:
    del session_factory
    request_json(
        "DELETE",
        f"/api/v1/inventory/libraries/{int(inventory_id)}",
        {"operator_username": str(operator_username or "").strip()},
    )
