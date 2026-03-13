from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.bin_info import BinInfo
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.category import Category, CategoryType
from shared.models.inventory import InventoryLibrary, InventoryLibraryStatus
from shared.models.merchant import Merchant
from shared.models.order import OrderItem
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "bot_library_purchase.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_rows(session_factory):
    session = session_factory()
    admin = AdminUser(
        username="merchant_admin",
        email="merchant_admin@local.test",
        password_hash="",
        role=AdminRole.MERCHANT,
        display_name="Merchant Admin",
        is_active=True,
        is_verified=True,
    )
    admin.set_password("merchant123")
    session.add(admin)
    session.commit()
    session.refresh(admin)

    merchant = Merchant(
        admin_user_id=int(admin.id or 0),
        name="Merchant A",
        is_active=True,
        is_verified=True,
        is_featured=False,
        total_products=10,
        sold_products=0,
    )
    session.add(merchant)
    session.commit()
    session.refresh(merchant)

    category = Category(
        name="全资库 一手",
        code="inventory_full_first_hand",
        type=CategoryType.POOL,
        base_price=7,
        min_price=5,
        is_active=True,
        is_visible=True,
    )
    session.add(category)
    session.commit()
    session.refresh(category)

    library_a = InventoryLibrary(
        name="库A",
        merchant_id=int(merchant.id or 0),
        category_id=int(category.id or 0),
        unit_price=8,
        pick_price=6,
        status=InventoryLibraryStatus.ACTIVE,
        is_bot_enabled=True,
        total_count=0,
        sold_count=0,
        remaining_count=0,
    )
    library_b = InventoryLibrary(
        name="库B",
        merchant_id=int(merchant.id or 0),
        category_id=int(category.id or 0),
        unit_price=8,
        pick_price=6,
        status=InventoryLibraryStatus.ACTIVE,
        is_bot_enabled=True,
        total_count=0,
        sold_count=0,
        remaining_count=0,
    )
    session.add(library_a)
    session.add(library_b)
    session.commit()
    session.refresh(library_a)
    session.refresh(library_b)

    bot = BotInstance(
        token="bot-token-100",
        name="Bot A",
        username="bot_a",
        status=BotStatus.ACTIVE,
        is_enabled=True,
        is_platform_bot=True,
    )
    session.add(bot)

    user = User(
        telegram_id=9001001001,
        username="buyer",
        first_name="Buyer",
        balance=120,
        total_deposit=120,
        total_spent=0,
        from_bot_id=None,
        is_banned=False,
    )
    session.add(user)
    session.commit()
    session.refresh(bot)
    session.refresh(user)
    user.from_bot_id = int(bot.id or 0)
    session.add(user)

    bin_rows = [
        BinInfo(
            bin_number="311111",
            country="US",
            country_code="US",
            bank_name="Bank 311111",
            card_brand="VISA",
            card_type="CREDIT",
            card_level="PLATINUM",
        ),
        BinInfo(
            bin_number="311112",
            country="US",
            country_code="US",
            bank_name="Bank 311112",
            card_brand="VISA",
            card_type="DEBIT",
            card_level="CLASSIC",
        ),
        BinInfo(
            bin_number="411111",
            country="US",
            country_code="US",
            bank_name="Bank 411111",
            card_brand="VISA",
            card_type="CREDIT",
            card_level="PLATINUM",
        ),
        BinInfo(
            bin_number="611111",
            country="US",
            country_code="US",
            bank_name="Bank 611111",
            card_brand="VISA",
            card_type="DEBIT",
            card_level="PLATINUM",
        ),
    ]
    for row in bin_rows:
        session.add(row)

    products = [
        ProductItem(
            raw_data=f"31111100000000{idx}|12/30|12{idx}",
            data_hash=f"h-311111-{idx}",
            bin_number="311111",
            category_id=int(category.id or 0),
            country_code="US",
            supplier_id=int(merchant.id or 0),
            inventory_library_id=int(library_a.id or 0),
            cost_price=4,
            selling_price=8,
            status=ProductStatus.AVAILABLE,
        )
        for idx in range(1, 3)
    ]
    products.extend(
        [
            ProductItem(
                raw_data="3111120000000001|12/30|999",
                data_hash="h-311112-1",
                bin_number="311112",
                category_id=int(category.id or 0),
                country_code="US",
                supplier_id=int(merchant.id or 0),
                inventory_library_id=int(library_a.id or 0),
                cost_price=4,
                selling_price=8,
                status=ProductStatus.AVAILABLE,
            ),
            ProductItem(
                raw_data="4111110000000001|12/30|123",
                data_hash="h-411111-1",
                bin_number="411111",
                category_id=int(category.id or 0),
                country_code="US",
                supplier_id=int(merchant.id or 0),
                inventory_library_id=int(library_a.id or 0),
                cost_price=4,
                selling_price=8,
                status=ProductStatus.AVAILABLE,
            ),
            ProductItem(
                raw_data="6111110000000001|12/30|321",
                data_hash="h-611111-1",
                bin_number="611111",
                category_id=int(category.id or 0),
                country_code="US",
                supplier_id=int(merchant.id or 0),
                inventory_library_id=int(library_b.id or 0),
                cost_price=4,
                selling_price=8,
                status=ProductStatus.AVAILABLE,
            ),
        ]
    )
    for row in products:
        session.add(row)
    session.commit()
    session.close()


def test_library_snapshot_and_bin_exports(tmp_path: Path):
    from services.bot_side_service import (
        export_bot_global_bins,
        export_bot_library_bins,
        get_bot_library_snapshot,
        list_bot_catalog_categories,
        list_bot_inventory_libraries,
    )

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    categories = list_bot_catalog_categories(catalog_type="full", session_factory=session_factory)
    assert len(categories) == 1
    assert categories[0]["library_count"] == 2

    rows = list_bot_inventory_libraries(category_id=1, session_factory=session_factory)
    assert len(rows) == 2
    assert rows[0]["name"] == "库A"

    snapshot = get_bot_library_snapshot(library_id=1, session_factory=session_factory)
    assert snapshot["library_name"] == "库A"
    assert snapshot["remaining_count"] == 4
    assert snapshot["prefix_counts"]["3C"] == 2
    assert snapshot["prefix_counts"]["3D"] == 1

    lib_bins = export_bot_library_bins(library_id=1, session_factory=session_factory)
    assert "311111" in lib_bins["content"]
    assert "411111" in lib_bins["content"]

    global_bins = export_bot_global_bins(session_factory=session_factory)
    assert "611111" in global_bins["content"]


def test_execute_head_purchase_and_order_item_snapshot(tmp_path: Path):
    from services.bot_side_service import execute_library_purchase, preview_head_purchase_bins, quote_library_purchase

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    preview = preview_head_purchase_bins(library_id=1, bins=["311111", "411111"], session_factory=session_factory)
    assert preview["missing_bins"] == []

    quote = quote_library_purchase(
        library_id=1,
        mode="head",
        quantity=1,
        bins=["311111", "411111"],
        session_factory=session_factory,
    )
    assert quote["total_units"] == 2
    assert quote["total_amount"] == 12.0

    result = execute_library_purchase(
        user_id=1,
        bot_id=1,
        library_id=1,
        mode="head",
        quantity=1,
        bins=["311111", "411111"],
        session_factory=session_factory,
    )
    assert result["total_units"] == 2
    assert len(result["raw_data_items"]) == 2

    session = session_factory()
    try:
        order_item = session.exec(select(OrderItem).order_by(OrderItem.id.asc())).first()
        assert order_item is not None
        assert order_item.purchase_mode == "head"
        assert '"mode":"head"' in str(order_item.purchase_filter_json or "")
    finally:
        session.close()


def test_search_libraries_by_bin(tmp_path: Path):
    from services.bot_side_service import search_bot_libraries_by_bin

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)
    rows = search_bot_libraries_by_bin(bin_number="311111", session_factory=session_factory)
    assert len(rows) == 1
    assert rows[0]["library_name"] == "库A"
