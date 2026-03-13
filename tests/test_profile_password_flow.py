from __future__ import annotations

import test_reflex.state.profile_state as profile_state_module
from test_reflex.state.profile_state import ProfileState


def test_profile_state_change_password_requires_confirmation_match():
    state = ProfileState()
    state.username = "admin"
    state.password_current = "admin123"
    state.password_new = "admin456"
    state.password_confirm = "admin789"

    event = state.change_password()
    assert "match" in str(event).lower()


def test_profile_state_change_password_calls_service_and_resets_fields(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_update_profile_password(**kwargs):
        captured.update(
            {
                "username": kwargs["username"],
                "old_password": kwargs["old_password"],
                "new_password": kwargs["new_password"],
            }
        )
        return {"ok": True, "username": kwargs["username"]}

    monkeypatch.setattr(profile_state_module, "update_profile_password", _fake_update_profile_password)

    state = ProfileState()
    state.username = "admin"
    state.show_password_modal = True
    state.password_current = "admin123"
    state.password_new = "Admin#Pass12345"
    state.password_confirm = "Admin#Pass12345"

    event = state.change_password()

    assert captured == {
        "username": "admin",
        "old_password": "admin123",
        "new_password": "Admin#Pass12345",
    }
    assert state.password_current == ""
    assert state.password_new == ""
    assert state.password_confirm == ""
    assert state.show_password_modal is False
    assert "password" in str(event).lower()
