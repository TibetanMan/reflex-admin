from __future__ import annotations

import pytest

from services import reflex_api as module
from services.security_errors import AuthRequiredError, PermissionDeniedError


def test_reflex_dispatch_routes_agent_campaign_update(monkeypatch):
    monkeypatch.setattr(
        module,
        "get_admin_profile_service",
        lambda **kwargs: {"role": "super_admin", "is_active": True},
    )
    monkeypatch.setattr(
        module,
        "upsert_agent_campaign_config_service",
        lambda **kwargs: {"agent_id": kwargs["agent_id"], "status": "active"},
    )

    row = module.dispatch_request(
        "PATCH",
        "/api/v1/agents/21/campaign",
        {
            "actor_username": "admin",
            "is_enabled": True,
            "first_deposit_bonus_rate": 0.05,
            "first_deposit_bonus_amount": 10,
        },
    )
    assert row["status"] == "active"


def test_route_policy_rejects_agent_campaign_update_without_actor(monkeypatch):
    monkeypatch.setattr(module, "upsert_agent_campaign_config_service", lambda **kwargs: {"status": "active"})

    with pytest.raises(AuthRequiredError):
        module.dispatch_request(
            "PATCH",
            "/api/v1/agents/21/campaign",
            {
                "is_enabled": True,
                "first_deposit_bonus_rate": 0.05,
                "first_deposit_bonus_amount": 10,
            },
        )


def test_route_policy_requires_super_admin_for_agent_campaign_update(monkeypatch):
    monkeypatch.setattr(
        module,
        "get_admin_profile_service",
        lambda **kwargs: {"role": "agent", "is_active": True},
    )
    monkeypatch.setattr(module, "upsert_agent_campaign_config_service", lambda **kwargs: {"status": "active"})

    with pytest.raises(PermissionDeniedError):
        module.dispatch_request(
            "PATCH",
            "/api/v1/agents/21/campaign",
            {
                "actor_username": "alice",
                "is_enabled": True,
                "first_deposit_bonus_rate": 0.05,
                "first_deposit_bonus_amount": 10,
            },
        )
