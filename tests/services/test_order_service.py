from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.category import Category, CategoryType
from shared.models.merchant import Merchant
from shared.models.order import Order, OrderItem, OrderStatus
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "order_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_order_rows(session_factory):
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

    merchant_admin = AdminUser(
        username="merchant1",
        email="merchant1@local.test",
        password_hash="",
        role=AdminRole.MERCHANT,
        display_name="Merchant One",
        is_active=True,
        is_verified=True,
    )
    merchant_admin.set_password("merchant123")
    session.add(merchant_admin)
    session.commit()
    session.refresh(merchant_admin)

    merchant = Merchant(
        admin_user_id=int(merchant_admin.id or 0),
        name="Merchant One",
        is_active=True,
        is_verified=True,
    )
    session.add(merchant)
    session.commit()
    session.refresh(merchant)

    bot = BotInstance(
        token="orders-bot-token",
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
        username="order_user",
        first_name="Order",
        last_name="User",
        balance=5.00,
        total_deposit=50.00,
        total_spent=25.00,
        from_bot_id=int(bot.id or 0),
        is_banned=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    category = Category(
        name="US VISA",
        code="US_VISA",
        type=CategoryType.POOL,
        base_price=5.0,
        min_price=3.0,
        is_active=True,
        is_visible=True,
    )
    session.add(category)
    session.commit()
    session.refresh(category)

    product = ProductItem(
        raw_data="4111111111111111|12/30|123|US",
        data_hash="order-service-product-hash",
        bin_number="411111",
        category_id=int(category.id or 0),
        country_code="US",
        supplier_id=int(merchant.id or 0),
        selling_price=25.00,
        cost_price=18.00,
        status=ProductStatus.SOLD,
        sold_to_user_id=int(user.id or 0),
        sold_to_bot_id=int(bot.id or 0),
        sold_price=25.00,
        sold_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    order = Order(
        order_no="ORD-TEST-0001",
        user_id=int(user.id or 0),
        bot_id=int(bot.id or 0),
        total_amount=25.00,
        paid_amount=25.00,
        items_count=1,
        status=OrderStatus.COMPLETED,
        paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    order_item = OrderItem(
        order_id=int(order.id or 0),
        product_id=int(product.id or 0),
        product_data=product.raw_data,
        category_name=category.name,
        bin_number=product.bin_number,
        country_code=product.country_code,
        unit_price=25.00,
        quantity=1,
        subtotal=25.00,
    )
    session.add(order_item)
    session.commit()
    session.close()


def test_list_orders_snapshot_returns_related_user_bot_and_item_rows(tmp_path: Path):
    from services.order_service import list_orders_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_order_rows(session_factory)

    rows = list_orders_snapshot(session_factory=session_factory)

    assert len(rows) == 1
    row = rows[0]
    assert row["order_no"] == "ORD-TEST-0001"
    assert row["status"] == "completed"
    assert row["bot"] == "Main Bot"
    assert "order_user" in row["user"]
    assert row["item_count"] == 1
    assert len(row["items"]) == 1
    assert row["items"][0]["merchant"] == "Merchant One"


def test_refund_order_updates_order_balance_ledger_and_audit(tmp_path: Path):
    from services.order_service import refund_order

    session_factory = _session_factory(tmp_path)
    _seed_order_rows(session_factory)

    result = refund_order(
        order_id=1,
        reason="user requested refund",
        operator_username="admin",
        session_factory=session_factory,
    )
    assert result["status"] == "refunded"
    assert result["refund_reason"] == "user requested refund"

    session = session_factory()
    order = session.exec(select(Order).where(Order.id == 1)).first()
    assert order is not None
    assert order.status == OrderStatus.REFUNDED
    assert order.refund_reason == "user requested refund"

    user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
    assert user is not None
    assert float(user.balance) == 30.00

    ledgers = session.exec(select(BalanceLedger)).all()
    assert len(ledgers) == 1
    assert ledgers[0].action == BalanceAction.REFUND
    assert float(ledgers[0].amount) == 25.00

    audits = session.exec(select(AdminAuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "orders.refund"
    session.close()


def test_get_order_snapshot_returns_single_row(tmp_path: Path):
    from services.order_service import get_order_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_order_rows(session_factory)

    row = get_order_snapshot(order_id=1, session_factory=session_factory)
    assert row["id"] == 1
    assert row["order_no"] == "ORD-TEST-0001"


def test_refresh_order_status_updates_pending_order_to_completed(tmp_path: Path):
    from services.order_service import refresh_order_status

    session_factory = _session_factory(tmp_path)
    _seed_order_rows(session_factory)

    session = session_factory()
    order = session.exec(select(Order).where(Order.id == 1)).first()
    assert order is not None
    order.status = OrderStatus.PENDING
    order.paid_amount = 25.00
    order.completed_at = None
    session.add(order)
    session.commit()
    session.close()

    refreshed = refresh_order_status(order_id=1, session_factory=session_factory)
    assert refreshed["id"] == 1
    assert refreshed["status"] == "completed"
