from __future__ import annotations

from services import reflex_api as module


def test_reflex_dispatch_routes_agent_campaign_update(monkeypatch):
    monkeypatch.setattr(module, "resolve_actor_profile_for_policy", lambda **kwargs: {"role": "super_admin"})
    monkeypatch.setattr(module, "enforce_route_policy", lambda **kwargs: None)
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
