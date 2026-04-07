from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "runtime_context_business_sync.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def test_ensure_runtime_identity_refreshes_bot_and_agent_user_truth(tmp_path: Path):
    from bot.runtime_context import ensure_runtime_identity

    session_factory = _session_factory(tmp_path)
    session = session_factory()
    try:
        agent_admin = AdminUser(
            username="agent-admin",
            email="agent-admin@local.test",
            password_hash="",
            role=AdminRole.AGENT,
            display_name="Agent Admin",
            is_active=True,
            is_verified=True,
        )
        agent_admin.set_password("agent123")
        session.add(agent_admin)
        session.commit()
        session.refresh(agent_admin)

        agent = Agent(
            admin_user_id=int(agent_admin.id or 0),
            name="Agent One",
            is_active=True,
            is_verified=True,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        bot = BotInstance(
            token="runtime-owned-bot-token",
            name="Runtime Owned Bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent.id or 0),
            total_users=999,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)
    finally:
        session.close()

    payload = ensure_runtime_identity(
        bot_token="runtime-owned-bot-token",
        bot_name="Runtime Owned Bot",
        bot_username="runtime_owned_bot",
        tg_user=SimpleNamespace(
            id=1234567890,
            username="runtime_user",
            first_name="Runtime",
            last_name="User",
            language_code="zh",
        ),
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(payload["bot_id"]))).first()
        agent = session.exec(select(Agent).where(Agent.name == "Agent One")).first()
    finally:
        session.close()

    assert bot is not None
    assert bot.total_users == 1
    assert agent is not None
    assert agent.total_users == 1


def test_ensure_runtime_identity_reconciles_old_and_new_bot_membership(tmp_path: Path):
    from bot.runtime_context import ensure_runtime_identity
    from shared.models.user import User

    session_factory = _session_factory(tmp_path)
    session = session_factory()
    try:
        agent_admin_one = AdminUser(
            username="agent-one",
            email="agent-one@local.test",
            password_hash="",
            role=AdminRole.AGENT,
            display_name="Agent One",
            is_active=True,
            is_verified=True,
        )
        agent_admin_one.set_password("agent123")
        session.add(agent_admin_one)
        session.commit()
        session.refresh(agent_admin_one)

        agent_admin_two = AdminUser(
            username="agent-two",
            email="agent-two@local.test",
            password_hash="",
            role=AdminRole.AGENT,
            display_name="Agent Two",
            is_active=True,
            is_verified=True,
        )
        agent_admin_two.set_password("agent123")
        session.add(agent_admin_two)
        session.commit()
        session.refresh(agent_admin_two)

        agent_one = Agent(
            admin_user_id=int(agent_admin_one.id or 0),
            name="Agent One",
            is_active=True,
            is_verified=True,
            total_users=1,
        )
        agent_two = Agent(
            admin_user_id=int(agent_admin_two.id or 0),
            name="Agent Two",
            is_active=True,
            is_verified=True,
        )
        session.add(agent_one)
        session.add(agent_two)
        session.commit()
        session.refresh(agent_one)
        session.refresh(agent_two)

        bot_one = BotInstance(
            token="old-bot-token",
            name="Old Bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent_one.id or 0),
            total_users=1,
        )
        bot_two = BotInstance(
            token="new-bot-token",
            name="New Bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent_two.id or 0),
            total_users=0,
        )
        session.add(bot_one)
        session.add(bot_two)
        session.commit()
        session.refresh(bot_one)
        session.refresh(bot_two)

        user = User(
            telegram_id=222333444,
            username="moving_user",
            first_name="Moving",
            from_bot_id=int(bot_one.id or 0),
        )
        session.add(user)
        session.commit()
    finally:
        session.close()

    ensure_runtime_identity(
        bot_token="new-bot-token",
        bot_name="New Bot",
        bot_username="new_bot",
        tg_user=SimpleNamespace(
            id=222333444,
            username="moving_user",
            first_name="Moving",
            last_name="User",
            language_code="zh",
        ),
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        bot_one = session.exec(select(BotInstance).where(BotInstance.token == "old-bot-token")).first()
        bot_two = session.exec(select(BotInstance).where(BotInstance.token == "new-bot-token")).first()
        agent_one = session.exec(select(Agent).where(Agent.name == "Agent One")).first()
        agent_two = session.exec(select(Agent).where(Agent.name == "Agent Two")).first()
    finally:
        session.close()

    assert bot_one is not None
    assert bot_one.total_users == 0
    assert bot_two is not None
    assert bot_two.total_users == 1
    assert agent_one is not None
    assert agent_one.total_users == 0
    assert agent_two is not None
    assert agent_two.total_users == 1
