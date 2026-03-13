"""HTTP-like API client wrappers for agent domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def list_agents_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/agents")
    return list(data) if isinstance(data, list) else []


def create_agent_with_bot(
    *,
    name: str,
    contact_telegram: str,
    contact_email: str,
    bot_name: str,
    bot_token: str,
    profit_rate: float,
    usdt_address: str,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/agents",
        {
            "name": name,
            "contact_telegram": contact_telegram,
            "contact_email": contact_email,
            "bot_name": bot_name,
            "bot_token": bot_token,
            "profit_rate": float(profit_rate),
            "usdt_address": usdt_address,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_agent_record(
    *,
    agent_id: int,
    name: str,
    contact_telegram: str,
    contact_email: str,
    bot_name: str,
    bot_token: str,
    profit_rate: float,
    usdt_address: str,
    is_verified: bool,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/agents/{int(agent_id)}",
        {
            "name": name,
            "contact_telegram": contact_telegram,
            "contact_email": contact_email,
            "bot_name": bot_name,
            "bot_token": bot_token,
            "profit_rate": float(profit_rate),
            "usdt_address": usdt_address,
            "is_verified": bool(is_verified),
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def toggle_agent_record_status(
    *,
    agent_id: int,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/agents/{int(agent_id)}/status",
    )
    return dict(data) if isinstance(data, dict) else {}
