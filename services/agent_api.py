"""HTTP-like API client wrappers for agent domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def _normalize_agent_row(item: Any) -> dict[str, Any]:
    row = dict(item) if isinstance(item, dict) else {}
    campaign = dict(row.get("campaign") or {})
    normalized_campaign = {
        "agent_id": int(row.get("id") or 0),
        "is_enabled": bool(campaign.get("is_enabled", False)),
        "status": str(campaign.get("status") or "disabled"),
        "summary": str(campaign.get("summary") or ""),
        "display_title": str(campaign.get("display_title") or ""),
        "display_subtitle": str(campaign.get("display_subtitle") or ""),
        "starts_at": campaign.get("starts_at"),
        "ends_at": campaign.get("ends_at"),
        "first_deposit_bonus_rate": float(campaign.get("first_deposit_bonus_rate") or 0),
        "first_deposit_bonus_amount": float(campaign.get("first_deposit_bonus_amount") or 0),
    }
    row["campaign"] = normalized_campaign
    row["campaign_status"] = normalized_campaign["status"]
    row["campaign_summary"] = normalized_campaign["summary"]
    row["campaign_title"] = normalized_campaign["display_title"]
    return row


def list_agents_snapshot(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/agents")
    return [_normalize_agent_row(item) for item in data] if isinstance(data, list) else []


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


def update_agent_campaign_config(
    *,
    agent_id: int,
    actor_username: str,
    is_enabled: bool,
    starts_at: str = "",
    ends_at: str = "",
    first_deposit_bonus_rate: float = 0.0,
    first_deposit_bonus_amount: float = 0.0,
    display_title: str = "",
    display_subtitle: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    payload = {
        "actor_username": str(actor_username or "").strip(),
        "is_enabled": bool(is_enabled),
        "starts_at": str(starts_at or "").strip(),
        "ends_at": str(ends_at or "").strip(),
        "first_deposit_bonus_rate": float(first_deposit_bonus_rate),
        "first_deposit_bonus_amount": float(first_deposit_bonus_amount),
        "display_title": str(display_title or "").strip(),
        "display_subtitle": str(display_subtitle or "").strip(),
    }
    data = request_json("PATCH", f"/api/v1/agents/{int(agent_id)}/campaign", payload)
    return dict(data) if isinstance(data, dict) else {}
