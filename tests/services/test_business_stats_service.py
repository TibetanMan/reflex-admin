from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.order import Order, OrderStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "business_stats_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_truth_rows(session_factory):
    session = session_factory()
    try:
        admin = AdminUser(
            username="agent-admin",
            email="agent-admin@local.test",
            password_hash="",
            role=AdminRole.AGENT,
            display_name="Agent Admin",
            is_active=True,
            is_verified=True,
        )
        admin.set_password("agent123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        agent = Agent(
            admin_user_id=int(admin.id or 0),
            name="Agent One",
            is_active=True,
            is_verified=True,
            balance=Decimal("4.50"),
            total_profit=Decimal("99.00"),
            frozen_balance=Decimal("88.00"),
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        bot_one = BotInstance(
            token="stats-bot-one",
            name="Stats Bot One",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent.id or 0),
            total_users=999,
            total_orders=999,
            total_revenue=999,
        )
        bot_two = BotInstance(
            token="stats-bot-two",
            name="Stats Bot Two",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent.id or 0),
            total_users=777,
            total_orders=777,
            total_revenue=777,
        )
        session.add(bot_one)
        session.add(bot_two)
        session.commit()
        session.refresh(bot_one)
        session.refresh(bot_two)

        user_one = User(
            telegram_id=100001,
            username="user_one",
            from_bot_id=int(bot_one.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        user_two = User(
            telegram_id=100002,
            username="user_two",
            from_bot_id=int(bot_one.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        session.add(user_one)
        session.add(user_two)
        session.commit()
        session.refresh(user_one)
        session.refresh(user_two)

        session.add(
            BotUserAccount(
                user_id=int(user_one.id or 0),
                bot_id=int(bot_one.id or 0),
                balance=Decimal("0.00"),
                total_deposit=Decimal("0.00"),
                total_spent=Decimal("0.00"),
            )
        )
        session.add(
            BotUserAccount(
                user_id=int(user_one.id or 0),
                bot_id=int(bot_two.id or 0),
                balance=Decimal("0.00"),
                total_deposit=Decimal("0.00"),
                total_spent=Decimal("0.00"),
            )
        )
        session.add(
            BotUserAccount(
                user_id=int(user_two.id or 0),
                bot_id=int(bot_one.id or 0),
                balance=Decimal("0.00"),
                total_deposit=Decimal("0.00"),
                total_spent=Decimal("0.00"),
            )
        )

        session.add(
            Order(
                order_no="AGENT-STATS-001",
                user_id=int(user_one.id or 0),
                bot_id=int(bot_one.id or 0),
                total_amount=Decimal("10.00"),
                paid_amount=Decimal("10.00"),
                items_count=1,
                status=OrderStatus.COMPLETED,
                agent_profit=Decimal("1.00"),
            )
        )
        session.add(
            Order(
                order_no="AGENT-STATS-002",
                user_id=int(user_two.id or 0),
                bot_id=int(bot_one.id or 0),
                total_amount=Decimal("7.00"),
                paid_amount=Decimal("7.00"),
                items_count=1,
                status=OrderStatus.REFUNDED,
                agent_profit=Decimal("0.70"),
            )
        )
        session.add(
            Order(
                order_no="AGENT-STATS-003",
                user_id=int(user_one.id or 0),
                bot_id=int(bot_two.id or 0),
                total_amount=Decimal("20.00"),
                paid_amount=Decimal("20.00"),
                items_count=1,
                status=OrderStatus.PAID,
                agent_profit=Decimal("2.00"),
            )
        )
        session.commit()

        return {
            "agent_id": int(agent.id or 0),
            "bot_one_id": int(bot_one.id or 0),
            "bot_two_id": int(bot_two.id or 0),
        }
    finally:
        session.close()


def test_business_truth_uses_live_metrics_not_stale_cached_fields(tmp_path: Path):
    from services.business_stats_service import get_agent_business_truth, get_bot_business_truth

    session_factory = _session_factory(tmp_path)
    seeded = _seed_truth_rows(session_factory)

    session = session_factory()
    try:
        bot_one = get_bot_business_truth(session, bot_id=seeded["bot_one_id"])
        bot_two = get_bot_business_truth(session, bot_id=seeded["bot_two_id"])
        agent = get_agent_business_truth(session, agent_id=seeded["agent_id"])
    finally:
        session.close()

    assert bot_one["total_users"] == 2
    assert bot_one["total_orders"] == 2
    assert float(bot_one["total_revenue"]) == 10.0

    assert bot_two["total_users"] == 1
    assert bot_two["total_orders"] == 1
    assert float(bot_two["total_revenue"]) == 20.0

    assert agent["total_users"] == 2
    assert agent["total_orders"] == 3
    assert float(agent["total_profit"]) == 3.0
    assert float(agent["frozen_balance"]) == 3.0
    assert float(agent["balance"]) == 4.5


def test_sync_business_fields_refreshes_stored_truth(tmp_path: Path):
    from services.business_stats_service import sync_agent_business_fields, sync_bot_business_fields

    session_factory = _session_factory(tmp_path)
    seeded = _seed_truth_rows(session_factory)

    session = session_factory()
    try:
        sync_bot_business_fields(session, bot_id=seeded["bot_one_id"])
        sync_bot_business_fields(session, bot_id=seeded["bot_two_id"])
        sync_agent_business_fields(session, agent_id=seeded["agent_id"])
        session.commit()

        bot_one = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_one_id"])).first()
        bot_two = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_two_id"])).first()
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert bot_one is not None
    assert bot_one.total_users == 2
    assert bot_one.total_orders == 2
    assert float(bot_one.total_revenue) == 10.0

    assert bot_two is not None
    assert bot_two.total_users == 1
    assert bot_two.total_orders == 1
    assert float(bot_two.total_revenue) == 20.0

    assert agent is not None
    assert agent.total_users == 2
    assert agent.total_orders == 3
    assert float(agent.total_profit) == 3.0
    assert float(agent.frozen_balance) == 3.0
    assert float(agent.balance) == 4.5
