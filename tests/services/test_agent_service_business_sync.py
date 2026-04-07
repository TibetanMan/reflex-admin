from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.order import Order, OrderStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "agent_service_business_sync.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_case(session_factory):
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

        bot = BotInstance(
            token="rebind-bot-token",
            name="Rebind Bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=True,
            total_users=999,
            total_orders=999,
            total_revenue=999,
        )
        session.add(bot)
        session.commit()
        session.refresh(agent)
        session.refresh(bot)

        user = User(
            telegram_id=909090,
            username="rebind_user",
            from_bot_id=int(bot.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(
            BotUserAccount(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                balance=Decimal("0.00"),
                total_deposit=Decimal("0.00"),
                total_spent=Decimal("0.00"),
            )
        )
        session.add(
            Order(
                order_no="REBIND-ORDER-001",
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                total_amount=Decimal("10.00"),
                paid_amount=Decimal("10.00"),
                items_count=1,
                status=OrderStatus.COMPLETED,
                agent_profit=Decimal("2.50"),
            )
        )
        session.commit()

        return {"bot_id": int(bot.id or 0), "agent_id": int(agent.id or 0)}
    finally:
        session.close()


def test_binding_existing_bot_to_agent_reconciles_truth_fields(tmp_path: Path):
    from services.agent_service import list_agents_snapshot
    from services.bot_service import get_bot_snapshot, update_bot_record

    session_factory = _session_factory(tmp_path)
    seeded = _seed_case(session_factory)

    update_bot_record(
        bot_id=seeded["bot_id"],
        name="Rebind Bot",
        owner_name="Agent One",
        usdt_address="TRX_REBIND",
        session_factory=session_factory,
    )

    agent_row = next(
        row for row in list_agents_snapshot(session_factory=session_factory)
        if int(row["id"]) == seeded["agent_id"]
    )
    bot_row = get_bot_snapshot(bot_id=seeded["bot_id"], session_factory=session_factory)

    session = session_factory()
    try:
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
        bot = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
    finally:
        session.close()

    assert bot_row["users"] == 1
    assert bot_row["orders"] == 1
    assert float(bot_row["revenue"]) == 10.0

    assert agent_row["total_users"] == 1
    assert agent_row["total_orders"] == 1
    assert float(agent_row["total_profit"]) == 2.5
    assert float(agent_row["frozen_balance"]) == 2.5
    assert float(agent_row["balance"]) == 0.0

    assert agent is not None
    assert agent.total_users == 1
    assert agent.total_orders == 1
    assert float(agent.total_profit) == 2.5
    assert float(agent.frozen_balance) == 2.5

    assert bot is not None
    assert bot.total_users == 1
    assert bot.total_orders == 1
    assert float(bot.total_revenue) == 10.0
