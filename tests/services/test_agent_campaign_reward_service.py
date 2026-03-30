from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel, Session, create_engine, select

from services.agent_campaign_service import upsert_agent_campaign_config
from services.agent_campaign_reward_service import apply_agent_campaign_reward_for_deposit
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.agent_campaign import CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.user import User


def _build_session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'campaign_reward_service.db'}")
    SQLModel.metadata.create_all(engine)
    return lambda: Session(engine)


def _seed_reward_case(session_factory):
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
            token="123456:ABCDEF_campaign_reward",
            name="Reward Bot",
            owner_agent_id=int(agent.id or 0),
            status=BotStatus.ACTIVE,
            is_enabled=True,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)

        user = User(
            telegram_id=123456789,
            username="reward_user",
            first_name="Reward",
            last_name="User",
            from_bot_id=int(bot.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        account = BotUserAccount(
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            balance=Decimal("50.00"),
            total_deposit=Decimal("50.00"),
            total_spent=Decimal("0.00"),
            order_count=0,
            is_banned=False,
        )
        session.add(account)

        deposit_first = Deposit(
            deposit_no="DEP_REWARD_001",
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            amount=Decimal("50.00"),
            actual_amount=Decimal("50.00"),
            method=DepositMethod.MANUAL,
            to_address="TRewardWallet1",
            status=DepositStatus.COMPLETED,
            completed_at=datetime(2026, 4, 10, 10, 0, 0),
        )
        session.add(deposit_first)

        deposit_second = Deposit(
            deposit_no="DEP_REWARD_002",
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            amount=Decimal("30.00"),
            actual_amount=Decimal("30.00"),
            method=DepositMethod.MANUAL,
            to_address="TRewardWallet1",
            status=DepositStatus.COMPLETED,
            completed_at=datetime(2026, 4, 11, 10, 0, 0),
        )
        session.add(deposit_second)
        session.commit()
    finally:
        session.close()

    upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2026-04-01 00:00:00",
        ends_at="2026-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.1000"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )


def test_apply_campaign_reward_for_first_bot_deposit_creates_grant_and_bonus_ledger(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    _seed_reward_case(session_factory)

    result = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
        account = session.exec(
            select(BotUserAccount).where(BotUserAccount.user_id == int(user.id or 0))
        ).first()
        grant = session.exec(select(CampaignRewardGrant)).first()
        bonus_ledger = session.exec(
            select(BalanceLedger).where(BalanceLedger.action == BalanceAction.CAMPAIGN_BONUS)
        ).first()
    finally:
        session.close()

    assert result["granted"] is True
    assert result["bonus_amount"] == 15.00
    assert grant is not None
    assert bonus_ledger is not None
    assert float(user.balance) == 15.00
    assert float(user.total_deposit) == 0.00
    assert float(account.balance) == 65.00
    assert float(account.total_deposit) == 50.00


def test_apply_campaign_reward_is_idempotent_for_same_user_and_bot(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    _seed_reward_case(session_factory)

    first = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)
    second = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)

    session = session_factory()
    try:
        grants = list(session.exec(select(CampaignRewardGrant)).all())
        bonus_ledgers = list(
            session.exec(select(BalanceLedger).where(BalanceLedger.action == BalanceAction.CAMPAIGN_BONUS)).all()
        )
    finally:
        session.close()

    assert first["granted"] is True
    assert second["granted"] is False
    assert len(grants) == 1
    assert len(bonus_ledgers) == 1


def test_second_completed_deposit_same_bot_gets_no_bonus(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    _seed_reward_case(session_factory)

    assert apply_agent_campaign_reward_for_deposit(deposit_id=2, session_factory=session_factory)["granted"] is False
