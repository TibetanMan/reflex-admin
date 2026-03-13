import inspect

import test_reflex.state.auth as auth_module
from test_reflex.state.auth import AuthState


def test_auth_state_login_uses_database_auth_service():
    source = inspect.getsource(AuthState.handle_login.fn)

    assert "authenticate_admin(" in source
    assert "TEST_USERS" not in source


def test_auth_state_sets_user_fields_on_successful_database_auth(monkeypatch):
    state = AuthState()
    state.login_username = "admin"
    state.login_password = "admin123"

    def _fake_authenticate_admin(username: str, password: str):
        assert username == "admin"
        assert password == "admin123"
        return {
            "id": 1,
            "username": "admin",
            "display_name": "Super Admin",
            "role": "super_admin",
            "avatar_url": "/avatar/admin.png",
            "is_active": True,
        }

    monkeypatch.setattr(auth_module, "authenticate_admin", _fake_authenticate_admin)

    state.handle_login()

    assert state.is_logged_in is True
    assert state.username == "admin"
    assert state.user_name == "Super Admin"
    assert state.user_role == "super_admin"
    assert state.user_avatar == "/avatar/admin.png"
    assert state.error_message == ""


def test_auth_state_returns_error_when_database_auth_fails(monkeypatch):
    state = AuthState()
    state.login_username = "admin"
    state.login_password = "wrong"

    def _fake_authenticate_admin(_username: str, _password: str):
        return None

    monkeypatch.setattr(auth_module, "authenticate_admin", _fake_authenticate_admin)

    state.handle_login()

    assert state.is_logged_in is False
    assert state.error_message != ""
