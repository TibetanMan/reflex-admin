from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.balance_ledger import BalanceLedger
from shared.models.bin_info import BinInfo
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.category import Category, CategoryType
from shared.models.deposit import Deposit
from shared.models.merchant import Merchant
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User
from shared.models.wallet import WalletAddress, WalletStatus


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "bot_side_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_rows(session_factory):
    session = session_factory()

    merchant_admin = AdminUser(
        username="merchant_bot",
        email="merchant_bot@local.test",
        password_hash="",
        role=AdminRole.MERCHANT,
        display_name="Merchant Bot",
        is_active=True,
        is_verified=True,
    )
    merchant_admin.set_password("merchant123")
    session.add(merchant_admin)
    session.commit()
    session.refresh(merchant_admin)

    merchant = Merchant(
        admin_user_id=int(merchant_admin.id or 0),
        name="Merchant Bot",
        description="Bot side merchant",
        is_active=True,
        is_verified=True,
        is_featured=True,
        total_products=4,
        sold_products=0,
    )
    session.add(merchant)
    session.commit()
    session.refresh(merchant)

    bot = BotInstance(
        token="bot-side-token-001",
        name="Bot Side Main",
        username="bot_side_main",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=True,
        usdt_address="TRX_BOT_SIDE",
    )
    session.add(bot)
    session.commit()
    session.refresh(bot)

    wallet = WalletAddress(
        address="TRX_BOT_SIDE_WALLET",
        bot_id=int(bot.id or 0),
        is_platform=True,
        label="Bot Side Wallet",
        status=WalletStatus.ACTIVE,
        balance=0.0,
        total_received=0.0,
    )
    session.add(wallet)

    user = User(
        telegram_id=7001001,
        username="bot_user",
        first_name="Bot",
        last_name="User",
        balance=50.0,
        total_deposit=120.0,
        total_spent=70.0,
        from_bot_id=int(bot.id or 0),
        is_banned=False,
    )
    session.add(user)

    category = Category(
        name="Full US",
        code="full_us",
        type=CategoryType.POOL,
        base_price=6.0,
        min_price=4.0,
        is_active=True,
        is_visible=True,
    )
    session.add(category)
    session.commit()
    session.refresh(user)
    session.refresh(category)

    session.add(
        BinInfo(
            bin_number="411111",
            country="United States",
            country_code="US",
            bank_name="Test Bank",
            bank_url="https://bank.example",
            bank_phone="+1-555-0000",
            card_brand="VISA",
            card_type="CREDIT",
            card_level="PLATINUM",
            card_category="CLASSIC",
            is_prepaid=False,
            is_commercial=False,
        )
    )

    for idx in range(1, 5):
        session.add(
            ProductItem(
                raw_data=f"41111111111111{idx:02d}|12/30|12{idx}",
                data_hash=f"bot-side-product-{idx}",
                bin_number="411111",
                category_id=int(category.id or 0),
                country_code="US",
                supplier_id=int(merchant.id or 0),
                cost_price=4.0,
                selling_price=8.5,
                status=ProductStatus.AVAILABLE,
            )
        )

    session.commit()
    session.close()


def test_bot_side_catalog_and_cart_checkout_flow(tmp_path: Path):
    from services.bot_side_service import (
        add_bot_cart_item,
        checkout_bot_order,
        get_bot_balance,
        get_bot_cart,
        get_bot_bin_info,
        list_bot_catalog_categories,
        list_bot_catalog_items,
        list_bot_merchant_items,
        list_bot_merchants,
        list_bot_orders,
        remove_bot_cart_item,
    )

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    categories = list_bot_catalog_categories(catalog_type="full", session_factory=session_factory)
    assert len(categories) == 1
    assert categories[0]["name"] == "Full US"

    items_payload = list_bot_catalog_items(
        category_id=categories[0]["id"],
        country="US",
        bin_number="411111",
        page=1,
        page_size=2,
        session_factory=session_factory,
    )
    assert items_payload["total"] == 4
    assert len(items_payload["items"]) == 2
    assert items_payload["items"][0]["status"] == "available"

    bin_row = get_bot_bin_info(bin_number="411111", session_factory=session_factory)
    assert bin_row["country_code"] == "US"

    merchants = list_bot_merchants(session_factory=session_factory)
    assert len(merchants) == 1
    merchant_items = list_bot_merchant_items(
        merchant_id=merchants[0]["id"],
        page=1,
        page_size=5,
        session_factory=session_factory,
    )
    assert merchant_items["total"] == 4

    cart_row = add_bot_cart_item(
        user_id=1,
        category_id=categories[0]["id"],
        quantity=1,
        category_query="full_us",
        session_factory=session_factory,
    )
    assert cart_row["quantity"] == 1

    cart_snapshot = get_bot_cart(user_id=1, session_factory=session_factory)
    assert cart_snapshot["total_quantity"] == 1
    assert cart_snapshot["can_checkout"] is True

    add_bot_cart_item(
        user_id=1,
        category_id=categories[0]["id"],
        quantity=2,
        category_query="full_us",
        session_factory=session_factory,
    )

    checkout = checkout_bot_order(user_id=1, bot_id=1, session_factory=session_factory)
    assert checkout["status"] == "completed"
    assert checkout["item_count"] == 3
    assert checkout["total_amount"] == 25.5

    balance = get_bot_balance(user_id=1, session_factory=session_factory)
    assert balance["balance"] == 24.5

    orders = list_bot_orders(user_id=1, session_factory=session_factory)
    assert orders["total"] == 1
    assert orders["orders"][0]["status"] == "completed"

    removable = add_bot_cart_item(
        user_id=1,
        category_id=categories[0]["id"],
        quantity=1,
        category_query="full_us",
        session_factory=session_factory,
    )
    removed = remove_bot_cart_item(
        cart_item_id=int(removable["id"]),
        user_id=1,
        session_factory=session_factory,
    )
    assert removed["ok"] is True


def test_bot_side_deposit_create_and_read(tmp_path: Path):
    from services.bot_side_service import create_bot_deposit, get_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    created = create_bot_deposit(
        user_id=1,
        amount=9.9,
        bot_id=1,
        session_factory=session_factory,
    )
    assert created["status"] == "pending"
    assert created["to_address"] == "TRX_BOT_SIDE_WALLET"

    row = get_bot_deposit(
        deposit_id=int(created["id"]),
        user_id=1,
        session_factory=session_factory,
    )
    assert row["id"] == int(created["id"])
    assert row["amount"] == 9.9


def test_create_bot_deposit_blocks_when_target_bot_wallet_missing(tmp_path: Path):
    import pytest

    from services.bot_side_service import create_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        rows = list(session.exec(select(WalletAddress)).all())
        for row in rows:
            session.delete(row)
        bot_two = BotInstance(
            token="bot-side-token-wallet-missing-001",
            name="Bot Without Wallet",
            username="bot_no_wallet",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_NO_WALLET",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)
    finally:
        session.close()

    with pytest.raises(ValueError, match="wallet"):
        create_bot_deposit(
            user_id=1,
            amount=9.9,
            bot_id=int(bot_two.id or 0),
            session_factory=session_factory,
        )


def test_create_bot_deposit_does_not_fallback_to_other_bot_wallet(tmp_path: Path):
    import pytest

    from services.bot_side_service import create_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        bot_two = BotInstance(
            token="bot-side-token-wallet-missing-002",
            name="Bot Two Missing Wallet",
            username="bot_two_no_wallet",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_TWO_NO_WALLET",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)
    finally:
        session.close()

    with pytest.raises(ValueError, match="wallet"):
        create_bot_deposit(
            user_id=1,
            amount=9.9,
            bot_id=int(bot_two.id or 0),
            session_factory=session_factory,
        )


def test_create_bot_deposit_uses_wallet_address_of_requested_bot(tmp_path: Path):
    from services.bot_side_service import create_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        bot_two = BotInstance(
            token="bot-side-token-wallet-present-002",
            name="Bot Two With Wallet",
            username="bot_two_wallet",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_TWO",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)
        session.add(
            WalletAddress(
                address="TRX_WALLET_BOT_2",
                bot_id=int(bot_two.id or 0),
                is_platform=False,
                label="Bot Two Wallet",
                status=WalletStatus.ACTIVE,
                balance=0.0,
                total_received=0.0,
            )
        )
        session.commit()
    finally:
        session.close()

    dep1 = create_bot_deposit(
        user_id=1,
        amount=10,
        bot_id=1,
        session_factory=session_factory,
    )
    dep2 = create_bot_deposit(
        user_id=1,
        amount=11,
        bot_id=2,
        session_factory=session_factory,
    )

    assert dep1["to_address"] == "TRX_BOT_SIDE_WALLET"
    assert dep2["to_address"] == "TRX_WALLET_BOT_2"


def test_get_bot_deposit_sync_onchain_marks_completed_and_persists_tx_hash(tmp_path: Path, monkeypatch):
    from services import deposit_chain_service
    from services.bot_side_service import create_bot_deposit, get_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    created = create_bot_deposit(
        user_id=1,
        amount=Decimal("9.90"),
        bot_id=1,
        session_factory=session_factory,
    )

    def _fake_query_usdt_inbound_transfers(**kwargs):
        assert kwargs["to_address"] == "TRX_BOT_SIDE_WALLET"
        return [
            {
                "tx_hash": "TRXHASH-COMPLETED-001",
                "to_address": "TRX_BOT_SIDE_WALLET",
                "from_address": "TRX_SOURCE_001",
                "amount": Decimal("9.90"),
                "confirmed": True,
                "contract_ret": "SUCCESS",
                "block_number": 9990001,
                "timestamp": datetime.utcnow(),
            }
        ]

    monkeypatch.setattr(
        deposit_chain_service,
        "query_usdt_inbound_transfers",
        _fake_query_usdt_inbound_transfers,
    )

    row = get_bot_deposit(
        deposit_id=int(created["id"]),
        user_id=1,
        bot_id=1,
        sync_onchain=True,
        session_factory=session_factory,
    )

    assert row["status"] == "completed"
    assert row["tx_hash"] == "TRXHASH-COMPLETED-001"
    assert row["actual_amount"] == 9.9

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.id == 1)).first()
        account = session.exec(
            select(BotUserAccount)
            .where(BotUserAccount.user_id == 1)
            .where(BotUserAccount.bot_id == 1)
        ).first()
        wallet = session.exec(select(WalletAddress).where(WalletAddress.bot_id == 1)).first()
        deposit = session.exec(select(Deposit).where(Deposit.id == int(created["id"]))).first()
        ledgers = list(session.exec(select(BalanceLedger)).all())
    finally:
        session.close()

    assert user is not None and float(user.balance) == 59.9
    assert user is not None and float(user.total_deposit) == 129.9
    assert account is not None and float(account.balance) == 59.9
    assert account is not None and float(account.total_deposit) == 129.9
    assert wallet is not None and float(wallet.balance) == 9.9
    assert wallet is not None and float(wallet.total_received) == 9.9
    assert deposit is not None and str(deposit.tx_hash) == "TRXHASH-COMPLETED-001"
    assert len(ledgers) == 1


def test_get_bot_deposit_sync_onchain_unconfirmed_marks_confirming(tmp_path: Path, monkeypatch):
    from services import deposit_chain_service
    from services.bot_side_service import create_bot_deposit, get_bot_deposit

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    created = create_bot_deposit(
        user_id=1,
        amount=Decimal("9.90"),
        bot_id=1,
        session_factory=session_factory,
    )

    def _fake_query_usdt_inbound_transfers(**kwargs):
        del kwargs
        return [
            {
                "tx_hash": "TRXHASH-PENDING-001",
                "to_address": "TRX_BOT_SIDE_WALLET",
                "from_address": "TRX_SOURCE_002",
                "amount": Decimal("9.90"),
                "confirmed": False,
                "contract_ret": "SUCCESS",
                "block_number": 9990002,
                "timestamp": datetime.utcnow(),
            }
        ]

    monkeypatch.setattr(
        deposit_chain_service,
        "query_usdt_inbound_transfers",
        _fake_query_usdt_inbound_transfers,
    )

    row = get_bot_deposit(
        deposit_id=int(created["id"]),
        user_id=1,
        bot_id=1,
        sync_onchain=True,
        session_factory=session_factory,
    )

    assert row["status"] == "confirming"
    assert row["tx_hash"] == "TRXHASH-PENDING-001"
    assert row["actual_amount"] == 9.9

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.id == 1)).first()
        account = session.exec(
            select(BotUserAccount)
            .where(BotUserAccount.user_id == 1)
            .where(BotUserAccount.bot_id == 1)
        ).first()
    finally:
        session.close()

    assert user is not None and float(user.balance) == 50.0
    assert account is not None and float(account.balance) == 50.0


def test_bot_side_balances_and_cart_are_isolated_by_bot(tmp_path: Path):
    from services.bot_side_service import (
        add_bot_cart_item,
        checkout_bot_order,
        get_bot_balance,
        get_bot_cart,
    )
    from shared.models.bot_user_account import BotUserAccount

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        bot_two = BotInstance(
            token="bot-side-token-002",
            name="Bot Side Alt",
            username="bot_side_alt",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_SIDE_ALT",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)

        accounts = [
            BotUserAccount(user_id=1, bot_id=1, balance=50.0, total_deposit=120.0, total_spent=70.0),
            BotUserAccount(user_id=1, bot_id=int(bot_two.id or 0), balance=7.0, total_deposit=7.0, total_spent=0.0),
        ]
        for row in accounts:
            session.add(row)
        session.commit()
    finally:
        session.close()

    add_bot_cart_item(
        user_id=1,
        bot_id=1,
        category_id=1,
        quantity=1,
        category_query="full_us",
        session_factory=session_factory,
    )
    cart_bot_one = get_bot_cart(user_id=1, bot_id=1, session_factory=session_factory)
    cart_bot_two = get_bot_cart(user_id=1, bot_id=2, session_factory=session_factory)
    assert cart_bot_one["total_quantity"] == 1
    assert cart_bot_two["total_quantity"] == 0

    checkout_bot_order(user_id=1, bot_id=1, session_factory=session_factory)
    balance_bot_one = get_bot_balance(user_id=1, bot_id=1, session_factory=session_factory)
    balance_bot_two = get_bot_balance(user_id=1, bot_id=2, session_factory=session_factory)
    assert balance_bot_one["balance"] == 41.5
    assert balance_bot_two["balance"] == 7.0


def test_checkout_updates_bots_snapshot_metrics(tmp_path: Path):
    from services.bot_service import list_bots_snapshot
    from services.bot_side_service import add_bot_cart_item, checkout_bot_order
    from shared.models.bot_user_account import BotUserAccount

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        session.add(BotUserAccount(user_id=1, bot_id=1, balance=50.0, total_deposit=120.0, total_spent=70.0))
        session.commit()
    finally:
        session.close()

    add_bot_cart_item(
        user_id=1,
        bot_id=1,
        category_id=1,
        quantity=3,
        category_query="full_us",
        session_factory=session_factory,
    )
    checkout_bot_order(user_id=1, bot_id=1, session_factory=session_factory)

    rows = list_bots_snapshot(session_factory=session_factory)
    row = next(item for item in rows if int(item["id"]) == 1)
    assert row["orders"] >= 1
    assert row["revenue"] >= 25.5
    assert row["users"] >= 1


def test_bot_scoped_ban_blocks_only_target_bot(tmp_path: Path):
    from services.bot_side_service import get_bot_balance
    from shared.models.bot_user_account import BotUserAccount

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        bot_two = BotInstance(
            token="bot-side-token-003",
            name="Bot Side Third",
            username="bot_side_third",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_SIDE_3",
        )
        session.add(bot_two)
        session.commit()
        session.refresh(bot_two)

        session.add(
            BotUserAccount(
                user_id=1,
                bot_id=1,
                balance=50.0,
                total_deposit=120.0,
                total_spent=70.0,
                is_banned=True,
            )
        )
        session.add(
            BotUserAccount(
                user_id=1,
                bot_id=int(bot_two.id or 0),
                balance=9.0,
                total_deposit=9.0,
                total_spent=0.0,
                is_banned=False,
            )
        )
        session.commit()
    finally:
        session.close()

    try:
        get_bot_balance(user_id=1, bot_id=1, session_factory=session_factory)
        assert False, "Expected bot-scoped ban to block bot_id=1"
    except ValueError as exc:
        assert "banned" in str(exc).lower()

    row = get_bot_balance(user_id=1, bot_id=2, session_factory=session_factory)
    assert row["balance"] == 9.0
