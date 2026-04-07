from __future__ import annotations

from decimal import Decimal

from sqlmodel import SQLModel, Session, create_engine, select

from services.agent_campaign_service import upsert_agent_campaign_config
from services.agent_campaign_reward_service import apply_agent_campaign_reward_for_deposit
from services.finance_service import create_manual_deposit, list_finance_deposits
from services.user_service import adjust_user_balance, list_users_snapshot
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.agent_campaign import CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit
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
        account = session.exec(
            select(BotUserAccount).where(BotUserAccount.user_id == int(user.id or 0))
        ).first()
        grants = list(session.exec(select(CampaignRewardGrant)).all())
        bonus_ledger = session.exec(
            select(BalanceLedger).where(BalanceLedger.action == BalanceAction.CAMPAIGN_BONUS)
        ).first()
    finally:
        session.close()
    snapshots = list_users_snapshot(session_factory=session_factory)
    snapshot = next(item for item in snapshots if str(item["telegram_id"]) == "123456789")

    assert payload["status"] == "completed"
    assert float(user.balance) == 40.50
    assert float(user.total_deposit) == 25.50
    assert float(account.balance) == 40.50
    assert float(account.total_deposit) == 25.50
    assert float(user.balance) == float(account.balance)
    assert float(user.total_deposit) == float(account.total_deposit)
    assert float(snapshot["balance"]) == 40.50
    assert float(snapshot["total_deposit"]) == 25.50
    assert len(grants) == 1
    assert bonus_ledger is not None

    second = apply_agent_campaign_reward_for_deposit(
        deposit_id=int(payload["id"] or 0),
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        grant_rows = list(session.exec(select(CampaignRewardGrant)).all())
        bonus_ledgers = list(
            session.exec(select(BalanceLedger).where(BalanceLedger.action == BalanceAction.CAMPAIGN_BONUS)).all()
        )
    finally:
        session.close()

    assert second["granted"] is False
    assert second["reason"] == "already_granted"
    assert len(grant_rows) == 1
    assert len(bonus_ledgers) == 1


def _seed_balance_adjust_case(session_factory):
    session = session_factory()
    try:
        admin = AdminUser(
            username="admin",
            email="admin-balance@example.com",
            password_hash="hashed",
            role=AdminRole.SUPER_ADMIN,
            display_name="Admin",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        bot = BotInstance(
            token="123456:ABCDEF_balance_adjust",
            name="Finance Bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)

        user = User(
            telegram_id=987654321,
            username="balance_user",
            first_name="Balance",
            last_name="User",
            from_bot_id=int(bot.id or 0),
            balance=Decimal("0.00"),
            total_deposit=Decimal("0.00"),
        )
        session.add(user)
        session.add(
            WalletAddress(
                address="TBalanceWallet1",
                bot_id=int(bot.id or 0),
                status=WalletStatus.ACTIVE,
                label="Balance Wallet",
                balance=Decimal("0.00"),
                total_received=Decimal("0.00"),
            )
        )
        session.commit()
        session.refresh(user)
        return {"user_id": int(user.id or 0), "bot_name": str(bot.name)}
    finally:
        session.close()


def test_adjust_user_balance_credit_creates_visible_manual_deposit_and_is_idempotent(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    seeded = _seed_balance_adjust_case(session_factory)

    first = adjust_user_balance(
        user_id=seeded["user_id"],
        action="credit",
        amount=Decimal("12.50"),
        remark="admin balance credit",
        source_bot_name=seeded["bot_name"],
        request_id="users-credit-001",
        operator_username="admin",
        session_factory=session_factory,
    )
    second = adjust_user_balance(
        user_id=seeded["user_id"],
        action="credit",
        amount=Decimal("12.50"),
        remark="admin balance credit",
        source_bot_name=seeded["bot_name"],
        request_id="users-credit-001",
        operator_username="admin",
        session_factory=session_factory,
    )

    finance_rows = list_finance_deposits(session_factory=session_factory)
    session = session_factory()
    try:
        deposits = list(session.exec(select(Deposit)).all())
        ledgers = list(
            session.exec(select(BalanceLedger).where(BalanceLedger.request_id == "users-credit-001")).all()
        )
        audits = list(
            session.exec(select(AdminAuditLog).where(AdminAuditLog.request_id == "users-credit-001")).all()
        )
    finally:
        session.close()

    assert first == second
    assert first["request_id"] == "users-credit-001"
    assert len(deposits) == 1
    assert len(ledgers) == 1
    assert len(audits) == 1
    assert any(row["deposit_no"] and row["method"] == "手动充值" and row["amount"] == 12.5 for row in finance_rows)


def test_adjust_user_balance_debit_does_not_create_deposit(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    seeded = _seed_balance_adjust_case(session_factory)

    adjust_user_balance(
        user_id=seeded["user_id"],
        action="credit",
        amount=Decimal("20.00"),
        remark="seed funds",
        source_bot_name=seeded["bot_name"],
        request_id="users-credit-seed",
        operator_username="admin",
        session_factory=session_factory,
    )
    adjust_user_balance(
        user_id=seeded["user_id"],
        action="debit",
        amount=Decimal("5.00"),
        remark="admin debit",
        source_bot_name=seeded["bot_name"],
        request_id="users-debit-001",
        operator_username="admin",
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        deposits = list(session.exec(select(Deposit)).all())
        debit_ledgers = list(
            session.exec(select(BalanceLedger).where(BalanceLedger.request_id == "users-debit-001")).all()
        )
    finally:
        session.close()

    assert len(deposits) == 1
    assert len(debit_ledgers) == 1
    assert debit_ledgers[0].action == BalanceAction.DEBIT
