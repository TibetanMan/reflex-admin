from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.order import Order, OrderStatus
from shared.models.user import User
from shared.models.user_export import UserBotSource


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "user_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_user_rows(session_factory):
    session = session_factory()

    admin = AdminUser(
        username="admin",
        email="admin@local.test",
        password_hash="",
        role=AdminRole.SUPER_ADMIN,
        display_name="Super Admin",
        is_active=True,
        is_verified=True,
    )
    admin.set_password("admin123")
    session.add(admin)
    session.commit()
    session.refresh(admin)

    bot_main = BotInstance(
        token="users-bot-main-token",
        name="Main Bot",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=True,
    )
    bot_alt = BotInstance(
        token="users-bot-alt-token",
        name="Alt Bot",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=False,
    )
    session.add(bot_main)
    session.add(bot_alt)
    session.commit()
    session.refresh(bot_main)
    session.refresh(bot_alt)

    user = User(
        telegram_id=777001,
        username="user_one",
        first_name="User",
        last_name="One",
        balance=25.00,
        total_deposit=110.00,
        total_spent=85.00,
        from_bot_id=int(bot_main.id or 0),
        is_banned=False,
        last_active_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(
        UserBotSource(
            user_id=int(user.id or 0),
            bot_id=int(bot_main.id or 0),
            is_primary=True,
        )
    )
    session.add(
        UserBotSource(
            user_id=int(user.id or 0),
            bot_id=int(bot_alt.id or 0),
            is_primary=False,
        )
    )
    session.add(
        BotUserAccount(
            user_id=int(user.id or 0),
            bot_id=int(bot_main.id or 0),
            balance=20.00,
            total_deposit=100.00,
            total_spent=80.00,
            order_count=1,
            is_banned=False,
        )
    )
    session.add(
        BotUserAccount(
            user_id=int(user.id or 0),
            bot_id=int(bot_alt.id or 0),
            balance=5.00,
            total_deposit=10.00,
            total_spent=5.00,
            order_count=0,
            is_banned=False,
        )
    )
    session.add(
        Deposit(
            deposit_no="DEP-USER-0001",
            user_id=int(user.id or 0),
            bot_id=int(bot_main.id or 0),
            amount=30.00,
            actual_amount=30.00,
            method=DepositMethod.MANUAL,
            to_address="TRX_MAIN",
            status=DepositStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            operator_remark="seed deposit",
        )
    )
    session.add(
        Order(
            order_no="ORD-USER-0001",
            user_id=int(user.id or 0),
            bot_id=int(bot_main.id or 0),
            total_amount=20.00,
            paid_amount=20.00,
            items_count=1,
            status=OrderStatus.COMPLETED,
            paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()
    session.close()


def test_list_users_snapshot_returns_sources_and_activity_records(tmp_path: Path):
    from services.user_service import list_users_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_user_rows(session_factory)

    rows = list_users_snapshot(session_factory=session_factory)
    assert len(rows) == 1

    user_row = rows[0]
    assert user_row["telegram_id"] == "777001"
    assert user_row["status"] == "active"
    assert user_row["primary_bot"] == "Main Bot"
    assert user_row["primary_bot_status"] == "active"
    assert len(user_row["bot_sources"]) == 2
    assert sum(float(row["balance"]) for row in user_row["bot_sources"]) == 25.0
    assert len(user_row["deposit_records"]) == 1
    assert user_row["deposit_records"][0]["record_no"] == "DEP-USER-0001"
    assert len(user_row["purchase_records"]) == 1
    assert user_row["purchase_records"][0]["order_no"] == "ORD-USER-0001"


def test_toggle_user_ban_supports_bot_scope_and_global_scope(tmp_path: Path):
    from services.user_service import toggle_user_ban

    session_factory = _session_factory(tmp_path)
    _seed_user_rows(session_factory)

    first = toggle_user_ban(
        user_id=1,
        operator_username="admin",
        scope="bot",
        source_bot_name="Main Bot",
        session_factory=session_factory,
    )
    assert first["scope"] == "bot"
    assert first["bot_status"] == "banned"

    second = toggle_user_ban(
        user_id=1,
        operator_username="admin",
        scope="global",
        session_factory=session_factory,
    )
    assert second["scope"] == "global"
    assert second["status"] == "banned"

    third = toggle_user_ban(
        user_id=1,
        operator_username="admin",
        scope="global",
        session_factory=session_factory,
    )
    assert third["status"] == "active"

    fourth = toggle_user_ban(
        user_id=1,
        operator_username="admin",
        scope="bot",
        source_bot_name="Main Bot",
        session_factory=session_factory,
    )
    assert fourth["bot_status"] == "active"

    session = session_factory()
    user = session.exec(select(User).where(User.id == 1)).first()
    main_account = session.exec(
        select(BotUserAccount).where(BotUserAccount.user_id == 1).where(BotUserAccount.bot_id == 1)
    ).first()
    alt_account = session.exec(
        select(BotUserAccount).where(BotUserAccount.user_id == 1).where(BotUserAccount.bot_id == 2)
    ).first()
    assert user is not None and user.is_banned is False
    assert main_account is not None and main_account.is_banned is False
    assert alt_account is not None and alt_account.is_banned is False

    audits = session.exec(select(AdminAuditLog)).all()
    assert len(audits) == 4
    assert any(row.action == "users.toggle_ban.bot" for row in audits)
    assert any(row.action == "users.toggle_ban.global" for row in audits)
    session.close()


def test_adjust_user_balance_updates_selected_bot_account_only(tmp_path: Path):
    from services.user_service import adjust_user_balance, list_users_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_user_rows(session_factory)

    result = adjust_user_balance(
        user_id=1,
        action="credit",
        amount=Decimal("12.34"),
        remark="manual topup",
        source_bot_name="Main Bot",
        request_id="req-001",
        operator_username="admin",
        session_factory=session_factory,
    )
    assert result["balance"] == 32.34
    assert result["total_deposit"] == 112.34

    duplicate = adjust_user_balance(
        user_id=1,
        action="credit",
        amount=Decimal("12.34"),
        remark="manual topup",
        source_bot_name="Main Bot",
        request_id="req-001",
        operator_username="admin",
        session_factory=session_factory,
    )
    assert duplicate["balance"] == 32.34

    session = session_factory()
    main_account = session.exec(
        select(BotUserAccount).where(BotUserAccount.user_id == 1).where(BotUserAccount.bot_id == 1)
    ).first()
    alt_account = session.exec(
        select(BotUserAccount).where(BotUserAccount.user_id == 1).where(BotUserAccount.bot_id == 2)
    ).first()
    user = session.exec(select(User).where(User.id == 1)).first()
    assert main_account is not None and float(main_account.balance) == 32.34
    assert main_account is not None and float(main_account.total_deposit) == 112.34
    assert alt_account is not None and float(alt_account.balance) == 5.00
    assert user is not None and float(user.balance) == 37.34
    assert user is not None and float(user.total_deposit) == 122.34

    ledgers = session.exec(select(BalanceLedger)).all()
    assert len(ledgers) == 1
    assert ledgers[0].action == BalanceAction.CREDIT
    assert str(ledgers[0].request_id) == "req-001"
    session.close()

    rows = list_users_snapshot(session_factory=session_factory)
    row = rows[0]
    assert row["balance"] == 37.34
    main_source = next(item for item in row["bot_sources"] if item["bot_name"] == "Main Bot")
    alt_source = next(item for item in row["bot_sources"] if item["bot_name"] == "Alt Bot")
    assert float(main_source["balance"]) == 32.34
    assert float(alt_source["balance"]) == 5.00


def test_user_detail_helpers_support_bot_filtered_records(tmp_path: Path):
    from services.user_service import (
        get_user_snapshot,
        list_user_deposit_records,
        list_user_purchase_records,
    )

    session_factory = _session_factory(tmp_path)
    _seed_user_rows(session_factory)

    row = get_user_snapshot(user_id=1, session_factory=session_factory)
    all_deposits = list_user_deposit_records(user_id=1, session_factory=session_factory)
    main_deposits = list_user_deposit_records(
        user_id=1,
        source_bot_name="Main Bot",
        session_factory=session_factory,
    )
    alt_deposits = list_user_deposit_records(
        user_id=1,
        source_bot_name="Alt Bot",
        session_factory=session_factory,
    )
    all_purchases = list_user_purchase_records(user_id=1, session_factory=session_factory)
    main_purchases = list_user_purchase_records(
        user_id=1,
        source_bot_name="Main Bot",
        session_factory=session_factory,
    )
    alt_purchases = list_user_purchase_records(
        user_id=1,
        source_bot_name="Alt Bot",
        session_factory=session_factory,
    )

    assert row["id"] == 1
    assert len(all_deposits) >= 1
    assert len(main_deposits) >= 1
    assert len(alt_deposits) == 0
    assert len(all_purchases) == 1
    assert len(main_purchases) == 1
    assert len(alt_purchases) == 0
