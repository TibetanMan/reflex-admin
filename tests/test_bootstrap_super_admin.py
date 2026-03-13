from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.user import User
from shared.models.wallet import WalletAddress


def _build_session(tmp_path: Path) -> Session:
    db_file = tmp_path / "bootstrap_super_admin.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_bootstrap_super_admin_creates_default_admin_with_hashed_password(tmp_path: Path):
    from shared.bootstrap import bootstrap_super_admin

    session = _build_session(tmp_path)
    user, created = bootstrap_super_admin(session, password="Admin#Pass12345")

    assert created is True
    assert user.username == "admin"
    assert user.role == AdminRole.SUPER_ADMIN
    assert user.password_hash != "Admin#Pass12345"
    assert user.verify_password("Admin#Pass12345") is True

    stored = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert stored is not None
    assert stored.role == AdminRole.SUPER_ADMIN


def test_bootstrap_super_admin_is_idempotent(tmp_path: Path):
    from shared.bootstrap import bootstrap_super_admin

    session = _build_session(tmp_path)
    first_user, first_created = bootstrap_super_admin(session, password="Admin#Pass12345")
    second_user, second_created = bootstrap_super_admin(session, password="Admin#Pass12345")

    assert first_created is True
    assert second_created is False
    assert first_user.id == second_user.id
    assert session.exec(select(AdminUser)).all().__len__() == 1


def test_run_startup_bootstrap_calls_init_then_super_admin_then_seed(monkeypatch):
    import shared.bootstrap as bootstrap_module

    calls: list[str] = []

    class _DummySession:
        def commit(self):
            calls.append("commit")

        def rollback(self):
            calls.append("rollback")

        def close(self):
            calls.append("close")

    def _fake_init_db():
        calls.append("init_db")

    def _fake_get_db_session():
        calls.append("open_session")
        return _DummySession()

    def _fake_bootstrap_super_admin(_session, password):
        calls.append("bootstrap_super_admin")
        calls.append(f"password:{password}")
        return None, False

    def _fake_bootstrap_seed_if_empty(_session):
        calls.append("bootstrap_seed_if_empty")
        return {}

    def _fake_bootstrap_bot_user_accounts(_session):
        calls.append("bootstrap_bot_user_accounts")
        return 0

    monkeypatch.setattr(bootstrap_module, "init_db", _fake_init_db)
    monkeypatch.setattr(bootstrap_module, "get_db_session", _fake_get_db_session)
    monkeypatch.setattr(bootstrap_module, "bootstrap_super_admin", _fake_bootstrap_super_admin)
    monkeypatch.setattr(bootstrap_module, "bootstrap_seed_if_empty", _fake_bootstrap_seed_if_empty)
    monkeypatch.setattr(bootstrap_module, "bootstrap_bot_user_accounts", _fake_bootstrap_bot_user_accounts)
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "Admin#Pass12345")

    bootstrap_module.run_startup_bootstrap()

    assert calls == [
        "init_db",
        "open_session",
        "bootstrap_super_admin",
        "password:Admin#Pass12345",
        "bootstrap_seed_if_empty",
        "bootstrap_bot_user_accounts",
        "commit",
        "close",
    ]


def test_run_startup_bootstrap_raises_on_weak_super_admin_password(monkeypatch):
    import pytest

    import shared.bootstrap as bootstrap_module
    from services.security_errors import SecurityPolicyError

    calls: list[str] = []

    class _DummySession:
        def commit(self):
            calls.append("commit")

        def rollback(self):
            calls.append("rollback")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(bootstrap_module, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(bootstrap_module, "get_db_session", lambda: _DummySession())
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "admin123")

    with pytest.raises(SecurityPolicyError, match="password"):
        bootstrap_module.run_startup_bootstrap()

    assert "rollback" in calls


def test_run_startup_bootstrap_accepts_strong_password(monkeypatch):
    import shared.bootstrap as bootstrap_module

    calls: list[str] = []

    class _DummySession:
        def commit(self):
            calls.append("commit")

        def rollback(self):
            calls.append("rollback")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(bootstrap_module, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(bootstrap_module, "get_db_session", lambda: _DummySession())
    monkeypatch.setattr(
        bootstrap_module,
        "bootstrap_super_admin",
        lambda _session, password: calls.append(f"bootstrap_super_admin:{password}") or (None, False),
    )
    monkeypatch.setattr(bootstrap_module, "bootstrap_seed_if_empty", lambda _session: calls.append("seed") or {})
    monkeypatch.setattr(bootstrap_module, "bootstrap_bot_user_accounts", lambda _session: calls.append("accounts") or 0)
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "Admin#Pass12345")

    bootstrap_module.run_startup_bootstrap()

    assert "bootstrap_super_admin:Admin#Pass12345" in calls
    assert "commit" in calls


def test_resolve_startup_password_falls_back_to_settings_when_env_missing(monkeypatch):
    import shared.bootstrap as bootstrap_module

    monkeypatch.delenv("SUPER_ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(
        bootstrap_module,
        "settings",
        type("_S", (), {"super_admin_password": "Admin#Pass12345"})(),
        raising=False,
    )

    assert bootstrap_module._resolve_startup_super_admin_password() == "Admin#Pass12345"


def test_bootstrap_seed_is_disabled_by_default(monkeypatch, tmp_path: Path):
    from shared.bootstrap import bootstrap_seed_if_empty, bootstrap_super_admin

    monkeypatch.delenv("BOOTSTRAP_DEMO_DATA_ENABLED", raising=False)
    session = _build_session(tmp_path)
    bootstrap_super_admin(session, password="Admin#Pass12345")

    seeded = bootstrap_seed_if_empty(session)
    assert seeded == {}
    assert session.exec(select(Agent)).first() is None
    assert session.exec(select(User)).first() is None
    assert session.exec(select(WalletAddress)).first() is None


def test_cleanup_bootstrap_demo_data_clears_seed_signatures(monkeypatch, tmp_path: Path):
    from shared.bootstrap import (
        bootstrap_seed_if_empty,
        bootstrap_super_admin,
        cleanup_bootstrap_demo_data,
    )

    monkeypatch.setenv("BOOTSTRAP_DEMO_DATA_ENABLED", "1")
    session = _build_session(tmp_path)
    bootstrap_super_admin(session, password="Admin#Pass12345")
    seeded = bootstrap_seed_if_empty(session)
    assert seeded

    removed = cleanup_bootstrap_demo_data(session)
    session.commit()
    assert removed

    assert (
        session.exec(
            select(User).where((User.username == "demo_user") | (User.telegram_id == 10000001))
        ).first()
        is None
    )
    assert (
        session.exec(
            select(WalletAddress).where(
                (WalletAddress.label == "Bootstrap Wallet")
                | (WalletAddress.address == "TRX_WALLET_BOOTSTRAP_001")
            )
        ).first()
        is None
    )
