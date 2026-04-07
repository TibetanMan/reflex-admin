from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine, select

from services.inventory_service import import_inventory_library
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.inventory import InventoryLibrary
from shared.models.merchant import Merchant
from shared.models.order import Order, OrderItem
from shared.models.product import ProductItem
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "bot_side_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_library_purchase_case(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    session = session_factory()
    try:
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

        merchant = Merchant(
            admin_user_id=int(admin.id or 0),
            name="Merchant One",
            fee_rate=0.10,
            is_active=True,
            is_verified=True,
        )
        session.add(merchant)
        session.commit()
        session.refresh(merchant)

        agent_admin = AdminUser(
            username="agent_owner",
            email="agent-owner@local.test",
            password_hash="",
            role=AdminRole.AGENT,
            display_name="Agent Owner",
            is_active=True,
            is_verified=True,
        )
        agent_admin.set_password("agent123")
        session.add(agent_admin)
        session.commit()
        session.refresh(agent_admin)

        agent = Agent(
            admin_user_id=int(agent_admin.id or 0),
            name="Agent Owner",
            profit_rate=0.10,
            is_active=True,
            is_verified=True,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        bot = BotInstance(
            token="bot-side-token-001",
            name="Bot Side",
            username="bot_side",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            owner_agent_id=int(agent.id or 0),
        )
        session.add(bot)
        session.commit()
        session.refresh(merchant)
        session.refresh(agent)
        session.refresh(bot)
        merchant_id = int(merchant.id or 0)
        bot_id = int(bot.id or 0)
        agent_id = int(agent.id or 0)

        user = User(
            telegram_id=9001001001,
            username="buyer",
            first_name="Buyer",
            from_bot_id=bot_id,
            balance=Decimal("200.00"),
            total_deposit=Decimal("200.00"),
            total_spent=Decimal("0.00"),
            is_banned=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = int(user.id or 0)
    finally:
        session.close()

    created = import_inventory_library(
        name="Merchant Library",
        merchant_name="Merchant One",
        category_name="全资库 一手",
        unit_price=20.0,
        pick_price=10.0,
        delimiter="|",
        content="\n".join(
            [
                "4111111111111111|12|2030|123|US",
                "4111112222222222|12|2030|123|US",
                "5555554444444444|12|2030|123|US",
            ]
        ),
        push_ad=False,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )

    return {
        "session_factory": session_factory,
        "library_id": int(created["library"]["id"]),
        "user_id": user_id,
        "bot_id": bot_id,
        "merchant_id": merchant_id,
        "agent_id": agent_id,
    }


def test_list_bot_merchant_items_returns_library_rows(tmp_path: Path):
    from services.bot_side_service import list_bot_merchant_items

    seeded = _seed_library_purchase_case(tmp_path)

    payload = list_bot_merchant_items(
        merchant_id=seeded["merchant_id"],
        page=1,
        page_size=8,
        session_factory=seeded["session_factory"],
    )

    assert payload["merchant_name"] == "Merchant One"
    assert payload["items"] == [
        {
            "id": seeded["library_id"],
            "name": "Merchant Library",
            "category_name": "全资库 一手",
            "remaining_count": 3,
        }
    ]


def test_add_bot_cart_item_refreshes_bot_and_agent_user_truth(tmp_path: Path):
    from services.bot_side_service import add_bot_cart_item

    seeded = _seed_library_purchase_case(tmp_path)

    add_bot_cart_item(
        user_id=seeded["user_id"],
        bot_id=seeded["bot_id"],
        category_id=1,
        quantity=1,
        session_factory=seeded["session_factory"],
    )

    session = seeded["session_factory"]()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert bot is not None
    assert bot.total_users == 1
    assert agent is not None
    assert agent.total_users == 1


def test_quote_library_purchase_uses_mode_specific_prices(tmp_path: Path):
    from services.bot_side_service import quote_library_purchase

    seeded = _seed_library_purchase_case(tmp_path)

    random_quote = quote_library_purchase(
        library_id=seeded["library_id"],
        mode="random",
        quantity=1,
        session_factory=seeded["session_factory"],
    )
    head_quote = quote_library_purchase(
        library_id=seeded["library_id"],
        mode="head",
        quantity=1,
        bins=["411111"],
        session_factory=seeded["session_factory"],
    )

    assert random_quote["unit_price"] == 20.0
    assert random_quote["total_amount"] == 20.0
    assert head_quote["unit_price"] == 10.0
    assert head_quote["total_amount"] == 10.0


def test_execute_library_purchase_uses_unit_price_for_random_mode(tmp_path: Path):
    from services.bot_side_service import execute_library_purchase

    seeded = _seed_library_purchase_case(tmp_path)

    payload = execute_library_purchase(
        user_id=seeded["user_id"],
        bot_id=seeded["bot_id"],
        library_id=seeded["library_id"],
        mode="random",
        quantity=1,
        session_factory=seeded["session_factory"],
    )

    session = seeded["session_factory"]()
    try:
        order = session.exec(select(Order).where(Order.id == int(payload["order_id"]))).first()
        order_item = session.exec(select(OrderItem).where(OrderItem.order_id == int(payload["order_id"]))).first()
        sold_row = session.exec(select(ProductItem).where(ProductItem.id == int(order_item.product_id))).first()
        bot = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert payload["unit_price"] == 20.0
    assert payload["total_amount"] == 20.0
    assert order is not None
    assert float(order.total_amount) == 20.0
    assert order_item is not None
    assert float(order_item.unit_price) == 20.0
    assert sold_row is not None
    assert float(sold_row.sold_price) == 20.0
    assert bot is not None
    assert bot.total_orders == 1
    assert float(bot.total_revenue) == 20.0
    assert agent is not None
    assert agent.total_orders == 1
    assert float(agent.total_profit) == 2.0
    assert float(agent.frozen_balance) == 2.0


def test_purchase_and_refund_keep_merchant_aggregates_in_sync(tmp_path: Path):
    from services.bot_side_service import execute_library_purchase
    from services.order_service import refund_order

    seeded = _seed_library_purchase_case(tmp_path)

    payload = execute_library_purchase(
        user_id=seeded["user_id"],
        bot_id=seeded["bot_id"],
        library_id=seeded["library_id"],
        mode="random",
        quantity=1,
        session_factory=seeded["session_factory"],
    )

    session = seeded["session_factory"]()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == seeded["merchant_id"])).first()
        order = session.exec(select(Order).where(Order.id == int(payload["order_id"]))).first()
        bot = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert merchant is not None
    assert merchant.sold_products == 1
    assert float(merchant.total_sales) == 20.0
    assert float(merchant.balance) == 0.0
    assert float(merchant.frozen_balance) == 18.0
    assert order is not None
    assert float(order.platform_profit) == 2.0
    assert float(order.supplier_profit) == 18.0
    assert float(order.agent_profit) == 2.0
    assert bot is not None
    assert bot.total_orders == 1
    assert float(bot.total_revenue) == 20.0
    assert agent is not None
    assert agent.total_orders == 1
    assert float(agent.total_profit) == 2.0
    assert float(agent.frozen_balance) == 2.0

    refund_order(
        order_id=int(payload["order_id"]),
        reason="customer requested refund",
        operator_username="admin",
        session_factory=seeded["session_factory"],
    )

    session = seeded["session_factory"]()
    try:
        merchant_after_refund = session.exec(
            select(Merchant).where(Merchant.id == seeded["merchant_id"])
        ).first()
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == seeded["library_id"])
        ).first()
        bot_after_refund = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
        agent_after_refund = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert merchant_after_refund is not None
    assert merchant_after_refund.sold_products == 0
    assert float(merchant_after_refund.total_sales) == 0.0
    assert float(merchant_after_refund.balance) == 0.0
    assert float(merchant_after_refund.frozen_balance) == 0.0
    assert library is not None
    assert library.sold_count == 0
    assert bot_after_refund is not None
    assert bot_after_refund.total_orders == 1
    assert float(bot_after_refund.total_revenue) == 0.0
    assert agent_after_refund is not None
    assert agent_after_refund.total_orders == 1
    assert float(agent_after_refund.total_profit) == 0.0
    assert float(agent_after_refund.frozen_balance) == 0.0


def test_checkout_bot_order_updates_merchant_aggregates(tmp_path: Path):
    from services.bot_side_service import add_bot_cart_item, checkout_bot_order

    seeded = _seed_library_purchase_case(tmp_path)

    add_bot_cart_item(
        user_id=seeded["user_id"],
        bot_id=seeded["bot_id"],
        category_id=1,
        quantity=1,
        session_factory=seeded["session_factory"],
    )
    payload = checkout_bot_order(
        user_id=seeded["user_id"],
        bot_id=seeded["bot_id"],
        session_factory=seeded["session_factory"],
    )

    session = seeded["session_factory"]()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == seeded["merchant_id"])).first()
        order = session.exec(select(Order).where(Order.id == int(payload["id"]))).first()
        bot = session.exec(select(BotInstance).where(BotInstance.id == seeded["bot_id"])).first()
        agent = session.exec(select(Agent).where(Agent.id == seeded["agent_id"])).first()
    finally:
        session.close()

    assert merchant is not None
    assert merchant.sold_products == 1
    assert float(merchant.total_sales) == 20.0
    assert float(merchant.balance) == 0.0
    assert float(merchant.frozen_balance) == 18.0
    assert order is not None
    assert float(order.platform_profit) == 2.0
    assert float(order.supplier_profit) == 18.0
    assert float(order.agent_profit) == 2.0
    assert bot is not None
    assert bot.total_orders == 1
    assert float(bot.total_revenue) == 20.0
    assert agent is not None
    assert agent.total_orders == 1
    assert float(agent.total_profit) == 2.0
    assert float(agent.frozen_balance) == 2.0
