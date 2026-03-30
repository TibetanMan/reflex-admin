from __future__ import annotations

from decimal import Decimal

from sqlmodel import SQLModel, Session, create_engine

from services.agent_campaign_service import upsert_agent_campaign_config
from services.bot_side_service import create_bot_deposit
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.user import User
from shared.models.wallet import WalletAddress, WalletStatus


def _build_session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bot_side_campaign_deposit.db'}")
    SQLModel.metadata.create_all(engine)
    return lambda: Session(engine)


def _seed_deposit_campaign_case(session_factory):
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

        bot = BotInstance(
            token="123456:ABCDEF_bot_campaign_deposit",
            name="Campaign Bot",
            owner_agent_id=int(agent.id or 0),
            status=BotStatus.ACTIVE,
            is_enabled=True,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)

        user = User(
            telegram_id=123456789,
            username="campaign_user",
            first_name="Campaign",
            from_bot_id=int(bot.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(
            WalletAddress(
                address="TCampaignDepositWallet001",
                bot_id=int(bot.id or 0),
                status=WalletStatus.ACTIVE,
            )
        )
        session.commit()
        return int(agent.id or 0), int(bot.id or 0), int(user.id or 0)
    finally:
        session.close()


def test_create_bot_deposit_returns_active_campaign_summary(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, bot_id, user_id = _seed_deposit_campaign_case(session_factory)

    upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2000-01-01 00:00:00",
        ends_at="2099-12-31 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    row = create_bot_deposit(user_id=user_id, amount=Decimal("100.00"), bot_id=bot_id, session_factory=session_factory)
    assert row["campaign"]["display_title"] == "首充活动"
    assert row["campaign"]["display_subtitle"] == "首次充值即可得奖励"
    assert row["campaign"]["summary"] == "首次充值赠送 5% + 10 USDT"
