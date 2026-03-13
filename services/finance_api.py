"""HTTP-like API client wrappers for finance domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_finance_deposits(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/finance/deposits")
    return list(data) if isinstance(data, list) else []


def list_finance_wallets(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/finance/wallets")
    return list(data) if isinstance(data, list) else []


def create_manual_deposit(
    *,
    user_identifier: str,
    amount: Any,
    remark: str,
    operator_username: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/finance/manual-deposit",
        {
            "user_identifier": user_identifier,
            "amount": str(amount),
            "remark": remark,
            "operator_username": operator_username,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def get_finance_wallet(
    wallet_id: int,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("GET", f"/api/v1/finance/wallets/{int(wallet_id)}")
    return dict(data) if isinstance(data, dict) else {}


def reconcile_finance_deposits(
    *,
    limit: int = 100,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/finance/deposits/reconcile",
        {"limit": int(limit)},
    )
    return dict(data) if isinstance(data, dict) else {}
