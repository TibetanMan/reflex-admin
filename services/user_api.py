"""HTTP-like API client wrappers for user domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_users_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/users")
    return list(data) if isinstance(data, list) else []


def toggle_user_ban(
    *,
    user_id: int,
    operator_username: str,
    scope: str = "global",
    source_bot_name: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/users/{int(user_id)}/ban",
        {
            "operator_username": operator_username,
            "scope": scope,
            "source_bot_name": source_bot_name,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def adjust_user_balance(
    *,
    user_id: int,
    action: str,
    amount: Any,
    remark: str,
    source_bot_name: str,
    request_id: str,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        f"/api/v1/users/{int(user_id)}/balance-adjust",
        {
            "action": action,
            "amount": str(amount),
            "remark": remark,
            "source_bot_name": source_bot_name,
            "request_id": request_id,
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def get_user_snapshot(
    user_id: int,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", f"/api/v1/users/{int(user_id)}")
    return dict(data) if isinstance(data, dict) else {}


def list_user_deposit_records(
    user_id: int,
    *,
    source_bot_name: str = "",
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    payload = {"source_bot_name": source_bot_name} if str(source_bot_name or "").strip() else None
    data = request_json("GET", f"/api/v1/users/{int(user_id)}/deposit-records", payload)
    return list(data) if isinstance(data, list) else []


def list_user_purchase_records(
    user_id: int,
    *,
    source_bot_name: str = "",
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    payload = {"source_bot_name": source_bot_name} if str(source_bot_name or "").strip() else None
    data = request_json("GET", f"/api/v1/users/{int(user_id)}/purchase-records", payload)
    return list(data) if isinstance(data, list) else []
