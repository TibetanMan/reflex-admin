from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "admin_account_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_admins(session_factory):
    session = session_factory()
    try:
        super_admin = AdminUser(
            username="admin",
            email="admin@local.test",
            password_hash="",
            role=AdminRole.SUPER_ADMIN,
            display_name="Super Admin",
            is_active=True,
            is_verified=True,
        )
        super_admin.set_password("Admin#Pass12345")
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
        agent_admin.set_password("Agent#Pass12345")
        session.add(agent_admin)

        session.commit()
    finally:
        session.close()


def test_create_admin_account_rejects_non_super_admin(tmp_path: Path):
    from services.admin_account_service import create_admin_account

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    with pytest.raises(PermissionError, match="super admin"):
        create_admin_account(
            actor_username="agent1",
            username="new_admin",
            display_name="New Admin",
            role="agent",
            session_factory=session_factory,
        )


def test_create_admin_account_generates_secure_initial_password(tmp_path: Path):
    from services.admin_account_service import create_admin_account

    session_factory = _session_factory(tmp_path)
    _seed_admins(session_factory)

    payload = create_admin_account(
        actor_username="admin",
        username="new_admin",
        display_name="New Admin",
        role="merchant",
        session_factory=session_factory,
    )

    assert payload["username"] == "new_admin"
    assert payload["role"] == "merchant"
    assert len(str(payload["initial_password"])) >= 12

    session = session_factory()
    try:
        row = session.exec(select(AdminUser).where(AdminUser.username == "new_admin")).first()
    finally:
        session.close()

    assert row is not None
    assert row.verify_password(str(payload["initial_password"])) is True
