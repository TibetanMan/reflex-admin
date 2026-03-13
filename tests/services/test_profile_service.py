from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "profile_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_admins(session_factory):
    session = session_factory()
    super_admin = AdminUser(
        username="admin",
        email="admin@local.test",
        password_hash="",
        role=AdminRole.SUPER_ADMIN,
        display_name="Super Admin",
        is_active=True,
        is_verified=True,
    )
    super_admin.set_password("admin123")
    session.add(super_admin)

    agent_admin = AdminUser(
        username="agent1",
        email="agent1@local.test",
        password_hash="",
        role=AdminRole.AGENT,
        display_name="Agent One",
        is_active=True,
        is_verified=True,
    )
    agent_admin.set_password("agent123")
    session.add(agent_admin)

    session.commit()
    session.close()


def test_get_profile_snapshot_reads_admin_user(tmp_path: Path):
    from services.profile_service import get_profile_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    row = get_profile_snapshot(username="admin", session_factory=session_factory)
    assert row["username"] == "admin"
    assert row["display_name"] == "Super Admin"
    assert row["role"] == AdminRole.SUPER_ADMIN.value


def test_get_profile_snapshot_raises_when_username_missing(tmp_path: Path):
    import pytest

    from services.profile_service import get_profile_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    with pytest.raises(ValueError, match="username"):
        get_profile_snapshot(username="", session_factory=session_factory)


def test_update_profile_snapshot_persists_changes(tmp_path: Path):
    from services.profile_service import update_profile_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    updated = update_profile_snapshot(
        username="admin",
        display_name="Admin Renamed",
        email="admin2@local.test",
        phone="13800000000",
        avatar_url="https://example.test/avatar.png",
        session_factory=session_factory,
    )
    assert updated["display_name"] == "Admin Renamed"
    assert updated["email"] == "admin2@local.test"
    assert updated["phone"] == "13800000000"
    assert updated["avatar_url"] == "https://example.test/avatar.png"

    session = session_factory()
    db_user = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    session.close()
    assert db_user is not None
    assert db_user.display_name == "Admin Renamed"
    assert db_user.email == "admin2@local.test"
    assert db_user.phone == "13800000000"


def test_update_profile_snapshot_raises_when_username_missing(tmp_path: Path):
    import pytest

    from services.profile_service import update_profile_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    with pytest.raises(ValueError, match="username"):
        update_profile_snapshot(
            username="",
            display_name="Admin Renamed",
            email="admin2@local.test",
            phone="13800000000",
            avatar_url="https://example.test/avatar.png",
            session_factory=session_factory,
        )


def test_update_profile_password_persists_new_hash(tmp_path: Path):
    from services.profile_service import update_profile_password

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    result = update_profile_password(
        username="admin",
        old_password="admin123",
        new_password="admin456",
        session_factory=session_factory,
    )
    assert result["ok"] is True

    session = session_factory()
    db_user = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    session.close()
    assert db_user is not None
    assert db_user.verify_password("admin456") is True


def test_update_profile_password_raises_when_username_missing(tmp_path: Path):
    import pytest

    from services.profile_service import update_profile_password

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    with pytest.raises(ValueError, match="username"):
        update_profile_password(
            username="",
            old_password="admin123",
            new_password="admin456",
            session_factory=session_factory,
        )
