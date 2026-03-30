from __future__ import annotations

from decimal import Decimal

from sqlmodel import SQLModel, Session, create_engine, select

from services.agent_campaign_service import upsert_agent_campaign_config
from services.finance_service import create_manual_deposit
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.user import User
from shared.models.wallet import WalletAddress, WalletStatus


def _build_session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'finance_service.db'}")
    SQLModel.metadata.create_all(engine)
    return lambda: Session(engine)


def _seed_finance_case(session_factory):
    agent_id = 0
    session = session_factory()
    try:
        admin = AdminUser(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            role=AdminRole.SUPER_ADMIN,
            display_name="Admin",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        agent = Agent(
            admin_user_id=int(admin.id or 0),
            name="Agent One",
            profit_rate=0.1,
            is_active=True,
            is_verified=True,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        agent_id = int(agent.id or 0)

        bot = BotInstance(
            token="123456:ABCDEF_finance_reward",
            name="Finance Bot",
            owner_agent_id=int(agent.id or 0),
            status=BotStatus.ACTIVE,
            is_enabled=True,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)

        user = User(
            telegram_id=123456789,
            username="finance_user",
            first_name="Finance",
            last_name="User",
            from_bot_id=int(bot.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
        )
        session.add(user)

        session.add(
            WalletAddress(
                address="TFinanceWallet1",
                bot_id=int(bot.id or 0),
                status=WalletStatus.ACTIVE,
                label="Finance Wallet",
                balance=Decimal("0.00"),
                total_received=Decimal("0.00"),
            )
        )
        session.commit()
    finally:
        session.close()

    upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2000-01-01 00:00:00",
        ends_at="2099-12-31 23:59:59",
        first_deposit_bonus_rate=Decimal("0.0000"),
        first_deposit_bonus_amount=Decimal("15.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )


def test_create_manual_deposit_applies_agent_campaign_bonus(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    _seed_finance_case(session_factory)

    payload = create_manual_deposit(
        user_identifier="123456789",
        amount=Decimal("25.50"),
        remark="manual test",
        operator_username="admin",
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
        bonus_ledger = session.exec(
            select(BalanceLedger).where(BalanceLedger.action == BalanceAction.CAMPAIGN_BONUS)
        ).first()
    finally:
        session.close()

    assert payload["status"] == "completed"
    assert float(user.balance) == 40.50
    assert float(user.total_deposit) == 25.50
    assert bonus_ledger is not None
