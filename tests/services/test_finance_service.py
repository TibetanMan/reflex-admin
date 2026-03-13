from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.balance_ledger import BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.deposit import Deposit
from shared.models.user import User
from shared.models.wallet import WalletAddress, WalletStatus


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "finance_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_finance_rows(session_factory):
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

    bot = BotInstance(
        token="finance-bot-token",
        name="Main Bot",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=True,
    )
    session.add(bot)
    session.commit()
    session.refresh(bot)

    user = User(
        telegram_id=123456789,
        username="demo_user",
        first_name="Demo",
        balance=0.0,
        total_deposit=0.0,
        total_spent=0.0,
        from_bot_id=int(bot.id or 0),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    wallet = WalletAddress(
        address="TRX_FINANCE_WALLET",
        bot_id=int(bot.id or 0),
        is_platform=True,
        label="Main Wallet",
        balance=0.0,
        total_received=0.0,
        status=WalletStatus.ACTIVE,
    )
    session.add(wallet)
    session.commit()
    session.close()


def test_create_manual_deposit_persists_deposit_and_balance_ledger(tmp_path: Path):
    from services.finance_service import create_manual_deposit

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)

    payload = create_manual_deposit(
        user_identifier="123456789",
        amount=Decimal("25.50"),
        remark="manual topup",
        operator_username="admin",
        session_factory=session_factory,
    )

    assert payload["status"] == "completed"
    assert payload["method"] == "手动充值"
    assert float(payload["amount"]) == 25.50

    session = session_factory()
    assert session.exec(select(Deposit)).all().__len__() == 1
    assert session.exec(select(BalanceLedger)).all().__len__() == 1
    user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
    assert user is not None
    assert float(user.balance) == 25.50
    session.close()


def test_create_manual_deposit_blocks_when_bot_wallet_missing(tmp_path: Path):
    import pytest

    from services.finance_service import create_manual_deposit

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)

    session = session_factory()
    try:
        bot_two = BotInstance(
            token="finance-bot-token-2",
            name="Second Bot No Wallet",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_TWO_FIELD",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)

        user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
        assert user is not None
        user.from_bot_id = int(bot_two.id or 0)
        session.add(user)
        session.commit()
    finally:
        session.close()

    with pytest.raises(ValueError, match="wallet"):
        create_manual_deposit(
            user_identifier="123456789",
            amount=Decimal("10.00"),
            remark="manual",
            operator_username="admin",
            session_factory=session_factory,
        )


def test_create_manual_deposit_does_not_fallback_to_bot_usdt_address(tmp_path: Path):
    import pytest

    from services.finance_service import create_manual_deposit

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(user.from_bot_id or 0))).first()
        wallets = list(session.exec(select(WalletAddress)).all())

        assert user is not None
        assert bot is not None
        for row in wallets:
            session.delete(row)
        bot.usdt_address = "TRX_FALLBACK_FIELD_ONLY"
        session.add(bot)
        session.commit()
    finally:
        session.close()

    with pytest.raises(ValueError, match="wallet"):
        create_manual_deposit(
            user_identifier="123456789",
            amount=Decimal("10.00"),
            remark="manual",
            operator_username="admin",
            session_factory=session_factory,
        )


def test_list_finance_views_return_deposit_and_wallet_rows(tmp_path: Path):
    from services.finance_service import (
        create_manual_deposit,
        list_finance_deposits,
        list_finance_wallets,
    )

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)
    create_manual_deposit(
        user_identifier="123456789",
        amount=Decimal("10.00"),
        remark="seed",
        operator_username="admin",
        session_factory=session_factory,
    )

    deposits = list_finance_deposits(session_factory=session_factory)
    wallets = list_finance_wallets(session_factory=session_factory)

    assert len(deposits) == 1
    assert deposits[0]["deposit_no"].startswith("DEP")
    assert deposits[0]["status"] == "completed"
    assert len(wallets) == 1
    assert wallets[0]["label"] == "Main Wallet"


def test_get_finance_wallet_returns_single_row(tmp_path: Path):
    from services.finance_service import get_finance_wallet

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)

    row = get_finance_wallet(wallet_id=1, session_factory=session_factory)
    assert row["id"] == 1
    assert row["address"] == "TRX_FINANCE_WALLET"


def test_reconcile_finance_deposits_syncs_pending_deposit(tmp_path: Path, monkeypatch):
    from services import deposit_chain_service
    from services.bot_side_service import create_bot_deposit
    from services.finance_service import list_finance_deposits, reconcile_finance_deposits

    session_factory = _session_factory(tmp_path)
    _seed_finance_rows(session_factory)

    created = create_bot_deposit(
        user_id=1,
        amount=Decimal("12.34"),
        bot_id=1,
        session_factory=session_factory,
    )

    def _fake_query_usdt_inbound_transfers(**kwargs):
        assert kwargs["to_address"] == "TRX_FINANCE_WALLET"
        return [
            {
                "tx_hash": "TRXHASH-FINANCE-001",
                "to_address": "TRX_FINANCE_WALLET",
                "from_address": "TRX_SOURCE_FINANCE",
                "amount": Decimal("12.34"),
                "confirmed": True,
                "contract_ret": "SUCCESS",
                "block_number": 8899001,
                "timestamp": datetime.utcnow(),
            }
        ]

    monkeypatch.setattr(
        deposit_chain_service,
        "query_usdt_inbound_transfers",
        _fake_query_usdt_inbound_transfers,
    )

    summary = reconcile_finance_deposits(limit=20, session_factory=session_factory)
    assert summary["total"] >= 1
    assert summary["completed"] >= 1
    assert summary["failed"] == 0

    deposits = list_finance_deposits(session_factory=session_factory)
    row = next(item for item in deposits if int(item["id"]) == int(created["id"]))
    assert row["status"] == "completed"
    assert row["tx_hash"] == "TRXHASH-FINANCE-001"
