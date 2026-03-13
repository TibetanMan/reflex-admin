from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "auth_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_admin_user(session_factory, *, is_active: bool = True):
    session = session_factory()
    user = AdminUser(
        username="admin",
        email="admin@local.test",
        password_hash="",
        role=AdminRole.SUPER_ADMIN,
        display_name="Super Admin",
        is_active=is_active,
        is_verified=True,
    )
    user.set_password("admin123")
    session.add(user)
    session.commit()
    session.close()


def test_authenticate_admin_returns_user_payload_when_credentials_are_valid(tmp_path: Path):
    from services.auth_service import authenticate_admin

    session_factory = _session_factory(tmp_path)
    _seed_admin_user(session_factory)

    payload = authenticate_admin("admin", "admin123", session_factory=session_factory)

    assert payload is not None
    assert payload["username"] == "admin"
    assert payload["role"] == AdminRole.SUPER_ADMIN.value
    assert payload["display_name"] == "Super Admin"
    assert payload["is_active"] is True

    session = session_factory()
    stored = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert stored is not None
    assert stored.last_login_at is not None
    session.close()


def test_authenticate_admin_returns_none_when_password_is_invalid(tmp_path: Path):
    from services.auth_service import authenticate_admin

    session_factory = _session_factory(tmp_path)
    _seed_admin_user(session_factory)

    payload = authenticate_admin("admin", "wrong-password", session_factory=session_factory)

    assert payload is None


def test_authenticate_admin_rejects_inactive_admin(tmp_path: Path):
    from services.auth_service import authenticate_admin

    session_factory = _session_factory(tmp_path)
    _seed_admin_user(session_factory, is_active=False)

    payload = authenticate_admin("admin", "admin123", session_factory=session_factory)

    assert payload is None


def test_get_admin_profile_returns_user_payload_when_active(tmp_path: Path):
    from services.auth_service import get_admin_profile

    session_factory = _session_factory(tmp_path)
    _seed_admin_user(session_factory)

    payload = get_admin_profile("admin", session_factory=session_factory)

    assert payload is not None
    assert payload["username"] == "admin"
    assert payload["role"] == AdminRole.SUPER_ADMIN.value


def test_refresh_admin_session_returns_tokens_for_active_user(tmp_path: Path):
    from services.auth_service import refresh_admin_session

    session_factory = _session_factory(tmp_path)
    _seed_admin_user(session_factory)

    payload = refresh_admin_session("admin", session_factory=session_factory)

    assert payload is not None
    assert str(payload["access_token"]).startswith("access-")
    assert str(payload["refresh_token"]).startswith("refresh-")
    assert payload["user"]["username"] == "admin"


def test_logout_admin_returns_ack_payload():
    from services.auth_service import logout_admin

    payload = logout_admin("admin")

    assert payload["ok"] is True
    assert payload["username"] == "admin"
