from __future__ import annotations

import services.agent_api as agent_api_module
import test_reflex.state.agent_state as agent_state_module


def test_open_campaign_modal_prefills_existing_agent_campaign():
    state = agent_state_module.AgentState()
    state.agents = [
        {
            "id": 7,
            "name": "Agent Seven",
            "campaign": {
                "is_enabled": True,
                "display_title": "首充活动",
                "display_subtitle": "首次充值即可得奖励",
                "starts_at": "2026-04-01 00:00:00",
                "ends_at": "2026-04-30 23:59:59",
                "first_deposit_bonus_rate": 0.05,
                "first_deposit_bonus_amount": 10.0,
                "summary": "首次充值赠送 5% + 10 USDT",
                "status": "active",
            },
        }
    ]

    state.open_campaign_modal(7)

    assert state.campaign_agent_id == 7
    assert state.show_campaign_modal is True
    assert state.campaign_enabled is True
    assert state.campaign_title == "首充活动"
    assert state.campaign_subtitle == "首次充值即可得奖励"
    assert state.campaign_starts_at == "2026-04-01 00:00:00"
    assert state.campaign_ends_at == "2026-04-30 23:59:59"
    assert state.campaign_bonus_rate == "0.0500"
    assert state.campaign_bonus_amount == "10.00"


def test_save_campaign_calls_api_with_normalized_payload(monkeypatch):
    captured: dict[str, object] = {}
    state = agent_state_module.AgentState()
    state.campaign_agent_id = 7
    state.campaign_enabled = True
    state.campaign_title = "首充活动"
    state.campaign_subtitle = "首次充值即可得奖励"
    state.campaign_starts_at = "2026-04-01 00:00:00"
    state.campaign_ends_at = "2026-04-30 23:59:59"
    state.campaign_bonus_rate = "5"
    state.campaign_bonus_amount = "10"

    monkeypatch.setattr(
        agent_state_module,
        "update_agent_campaign_config",
        lambda **kwargs: captured.update(kwargs) or {"status": "active"},
    )
    monkeypatch.setattr(agent_state_module, "list_agents_snapshot", lambda: [])

    state.save_campaign_config("admin")

    assert captured["agent_id"] == 7
    assert captured["actor_username"] == "admin"
    assert captured["is_enabled"] is True
    assert captured["starts_at"] == "2026-04-01 00:00:00"
    assert captured["ends_at"] == "2026-04-30 23:59:59"
    assert captured["first_deposit_bonus_rate"] == 0.05
    assert captured["first_deposit_bonus_amount"] == 10.0
    assert captured["display_title"] == "首充活动"
    assert captured["display_subtitle"] == "首次充值即可得奖励"


def test_save_campaign_requires_operator_username(monkeypatch):
    called = False
    state = agent_state_module.AgentState()
    state.campaign_agent_id = 7
    state.campaign_bonus_rate = "0.0500"
    state.campaign_bonus_amount = "10.00"

    def _fake_update(**kwargs):
        nonlocal called
        del kwargs
        called = True
        return {"status": "active"}

    monkeypatch.setattr(agent_state_module, "update_agent_campaign_config", _fake_update)

    state.save_campaign_config("")

    assert called is False


def test_save_campaign_rejects_non_finite_values(monkeypatch):
    called = False
    state = agent_state_module.AgentState()
    state.campaign_agent_id = 7
    state.campaign_bonus_rate = "NaN"
    state.campaign_bonus_amount = "10.00"

    def _fake_update(**kwargs):
        nonlocal called
        del kwargs
        called = True
        return {"status": "active"}

    monkeypatch.setattr(agent_state_module, "update_agent_campaign_config", _fake_update)

    state.save_campaign_config("admin")

    assert called is False


def test_list_agents_snapshot_normalizes_missing_campaign(monkeypatch):
    monkeypatch.setattr(
        agent_api_module,
        "request_json",
        lambda method, path: [{"id": 3, "name": "Agent Three"}] if method == "GET" and path == "/api/v1/agents" else [],
    )

    rows = agent_api_module.list_agents_snapshot()

    assert rows[0]["campaign"]["status"] == "disabled"
    assert rows[0]["campaign"]["summary"] == ""
    assert rows[0]["campaign"]["display_title"] == ""
