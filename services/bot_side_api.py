"""HTTP-like API client wrappers for bot-side endpoints."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_bot_catalog_categories(
    *,
    catalog_type: str = "full",
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    payload: dict[str, Any] = {"type": catalog_type}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("GET", "/api/v1/bot/catalog/categories", payload)
    return list(data) if isinstance(data, list) else []


def list_bot_catalog_items(
    *,
    category_id: Optional[int] = None,
    country: str = "",
    bin_number: str = "",
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {
        "country": country,
        "bin": bin_number,
        "page": int(page),
        "page_size": int(page_size),
    }
    if category_id not in (None, ""):
        payload["category_id"] = int(category_id)
    data = request_json("GET", "/api/v1/bot/catalog/items", payload)
    return dict(data) if isinstance(data, dict) else {}


def get_bot_bin_info(
    bin_number: str,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", f"/api/v1/bot/bin/{str(bin_number).strip()}")
    return dict(data) if isinstance(data, dict) else {}


def list_bot_merchants(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/bot/merchants")
    return list(data) if isinstance(data, list) else []


def list_bot_merchant_items(
    *,
    merchant_id: int,
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "GET",
        f"/api/v1/bot/merchants/{int(merchant_id)}/items",
        {"page": int(page), "page_size": int(page_size)},
    )
    return dict(data) if isinstance(data, dict) else {}


def add_bot_cart_item(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    category_id: Optional[int] = None,
    quantity: int = 1,
    category_query: str = "",
    country: str = "",
    bin_number: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {
        "user_id": int(user_id),
        "quantity": int(quantity),
        "category_query": category_query,
        "country": country,
        "bin": bin_number,
    }
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    if category_id not in (None, ""):
        payload["category_id"] = int(category_id)
    data = request_json("POST", "/api/v1/bot/cart/items", payload)
    return dict(data) if isinstance(data, dict) else {}


def get_bot_cart(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {"user_id": int(user_id)}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("GET", "/api/v1/bot/cart", payload)
    return dict(data) if isinstance(data, dict) else {}


def remove_bot_cart_item(
    *,
    cart_item_id: int,
    user_id: Optional[int] = None,
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {}
    if user_id not in (None, ""):
        payload["user_id"] = int(user_id)
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    if not payload:
        payload = None  # type: ignore[assignment]
    data = request_json("DELETE", f"/api/v1/bot/cart/items/{int(cart_item_id)}", payload)
    return dict(data) if isinstance(data, dict) else {}


def checkout_bot_order(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {"user_id": int(user_id)}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("POST", "/api/v1/bot/orders/checkout", payload)
    return dict(data) if isinstance(data, dict) else {}


def list_bot_orders(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {
        "user_id": int(user_id),
        "page": int(page),
        "page_size": int(page_size),
    }
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("GET", "/api/v1/bot/orders", payload)
    return dict(data) if isinstance(data, dict) else {}


def create_bot_deposit(
    *,
    user_id: int,
    amount: float | int | str,
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {"user_id": int(user_id), "amount": amount}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("POST", "/api/v1/bot/deposits/create", payload)
    return dict(data) if isinstance(data, dict) else {}


def get_bot_deposit(
    *,
    deposit_id: int,
    user_id: int,
    bot_id: Optional[int] = None,
    sync_onchain: bool = True,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {"user_id": int(user_id), "sync_onchain": bool(sync_onchain)}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json(
        "GET",
        f"/api/v1/bot/deposits/{int(deposit_id)}",
        payload,
    )
    return dict(data) if isinstance(data, dict) else {}


def get_bot_balance(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload: dict[str, Any] = {"user_id": int(user_id)}
    if bot_id not in (None, ""):
        payload["bot_id"] = int(bot_id)
    data = request_json("GET", "/api/v1/bot/balance", payload)
    return dict(data) if isinstance(data, dict) else {}
