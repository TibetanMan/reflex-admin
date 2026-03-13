from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser


def _build_session(tmp_path: Path) -> Session:
    db_file = tmp_path / "bootstrap_super_admin.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_bootstrap_super_admin_creates_default_admin_with_hashed_password(tmp_path: Path):
    from shared.bootstrap import bootstrap_super_admin

    session = _build_session(tmp_path)
    user, created = bootstrap_super_admin(session)

    assert created is True
    assert user.username == "admin"
    assert user.role == AdminRole.SUPER_ADMIN
    assert user.password_hash != "admin123"
    assert user.verify_password("admin123") is True

    stored = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert stored is not None
    assert stored.role == AdminRole.SUPER_ADMIN


def test_bootstrap_super_admin_is_idempotent(tmp_path: Path):
    from shared.bootstrap import bootstrap_super_admin

    session = _build_session(tmp_path)
    first_user, first_created = bootstrap_super_admin(session)
    second_user, second_created = bootstrap_super_admin(session)

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

    def _fake_bootstrap_super_admin(_session):
        calls.append("bootstrap_super_admin")
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

    bootstrap_module.run_startup_bootstrap()

    assert calls == [
        "init_db",
        "open_session",
        "bootstrap_super_admin",
        "bootstrap_seed_if_empty",
        "bootstrap_bot_user_accounts",
        "commit",
        "close",
    ]
