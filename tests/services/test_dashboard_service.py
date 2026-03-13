from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.category import Category, CategoryType
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.order import Order, OrderStatus
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "dashboard_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_rows(session_factory):
    session = session_factory()

    bot = BotInstance(
        token="dashboard-bot-token",
        name="Dashboard Bot",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=True,
        total_users=5,
        total_orders=6,
        total_revenue=80.0,
    )
    session.add(bot)
    session.commit()
    session.refresh(bot)

    user = User(
        telegram_id=10001,
        username="dash_user",
        first_name="Dash",
        balance=20,
        total_deposit=30,
        total_spent=10,
        from_bot_id=int(bot.id or 0),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    category = Category(
        name="US VISA",
        code="US_VISA_DASH",
        type=CategoryType.POOL,
        base_price=5,
        min_price=3,
        product_count=10,
        sold_count=7,
        is_active=True,
        is_visible=True,
    )
    session.add(category)
    session.commit()
    session.refresh(category)

    session.add(
        ProductItem(
            raw_data="4111111111111111|12/30|123|US",
            data_hash="dashboard-product-hash-1",
            bin_number="411111",
            category_id=int(category.id or 0),
            country_code="US",
            selling_price=5.0,
            status=ProductStatus.AVAILABLE,
        )
    )
    session.add(
        Order(
            order_no="ORD-DASH-001",
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            total_amount=10.0,
            paid_amount=10.0,
            items_count=2,
            status=OrderStatus.COMPLETED,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    session.add(
        Deposit(
            deposit_no="DEP-DASH-001",
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            amount=30.0,
            actual_amount=30.0,
            method=DepositMethod.MANUAL,
            to_address="TRX_DASH",
            status=DepositStatus.COMPLETED,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()
    session.close()


def test_get_dashboard_snapshot_returns_expected_sections(tmp_path: Path):
    from services.dashboard_service import get_dashboard_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    data = get_dashboard_snapshot(session_factory=session_factory)
    assert data["today_sales"] >= 0
    assert data["today_orders"] >= 0
    assert data["new_users"] >= 0
    assert data["total_stock"] >= 0

    assert isinstance(data["sales_chart_data"], list)
    assert isinstance(data["top_categories"], list)
    assert isinstance(data["recent_orders"], list)
    assert isinstance(data["recent_deposits"], list)
    assert isinstance(data["bot_stats"], list)


def test_dashboard_service_exposes_extended_query_helpers(tmp_path: Path):
    from services.dashboard_service import (
        list_bot_status,
        list_recent_deposits,
        list_recent_orders,
        list_top_categories,
    )

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    recent_orders = list_recent_orders(limit=1, session_factory=session_factory)
    recent_deposits = list_recent_deposits(limit=1, session_factory=session_factory)
    top_categories = list_top_categories(limit=1, session_factory=session_factory)
    bot_status = list_bot_status(limit=1, session_factory=session_factory)

    assert len(recent_orders) == 1
    assert len(recent_deposits) == 1
    assert len(top_categories) == 1
    assert len(bot_status) == 1


def test_top_categories_uses_real_product_status_counts(tmp_path: Path):
    from services.dashboard_service import get_dashboard_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        category = session.exec(select(Category).where(Category.name == "US VISA")).first()
        assert category is not None

        # Deliberately make category counters wrong; dashboard should use real product rows.
        category.product_count = 999
        category.sold_count = 888
        session.add(category)
        session.add(
            ProductItem(
                raw_data="4222222222222222|01/31|321|US",
                data_hash="dashboard-product-hash-2",
                bin_number="422222",
                category_id=int(category.id or 0),
                country_code="US",
                selling_price=6.0,
                status=ProductStatus.SOLD,
            )
        )
        session.commit()
    finally:
        session.close()

    data = get_dashboard_snapshot(session_factory=session_factory)
    target = next((item for item in data["top_categories"] if item["name"] == "US VISA"), None)
    assert target is not None
    assert int(target["sales"]) == 1
    assert int(target["stock"]) == 1


def test_dashboard_snapshot_recent_orders_defaults_to_ten_rows(tmp_path: Path):
    from services.dashboard_service import get_dashboard_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        user = session.exec(select(User).where(User.username == "dash_user")).first()
        bot = session.exec(select(BotInstance).where(BotInstance.name == "Dashboard Bot")).first()
        assert user is not None
        assert bot is not None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for index in range(12):
            session.add(
                Order(
                    order_no=f"ORD-DASH-{index + 2:03d}",
                    user_id=int(user.id or 0),
                    bot_id=int(bot.id or 0),
                    total_amount=10.0 + float(index),
                    paid_amount=10.0 + float(index),
                    items_count=1,
                    status=OrderStatus.COMPLETED,
                    created_at=now.replace(microsecond=index),
                    completed_at=now.replace(microsecond=index),
                    paid_at=now.replace(microsecond=index),
                )
            )
        session.commit()
    finally:
        session.close()

    data = get_dashboard_snapshot(session_factory=session_factory)
    assert len(list(data.get("recent_orders") or [])) == 10
