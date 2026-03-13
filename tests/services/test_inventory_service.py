from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.category import Category, CategoryType
from shared.models.merchant import Merchant

PLATFORM_MERCHANT_NAME = "平台自营"
DEFAULT_CATEGORY_NAME = "全资库 一手"


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "inventory_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_base_rows(session_factory):
    session = session_factory()

    super_admin = AdminUser(
        username="admin",
        email="admin@local.test",
        password_hash="",
        role=AdminRole.SUPER_ADMIN,
        display_name="Super Admin",
        is_active=True,
        is_verified=True,
    )
    super_admin.set_password("admin123")
    session.add(super_admin)
    session.commit()
    session.refresh(super_admin)

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
        name=PLATFORM_MERCHANT_NAME,
        is_active=True,
        is_verified=True,
    )
    category = Category(
        name=DEFAULT_CATEGORY_NAME,
        code="inventory_cat_1",
        type=CategoryType.POOL,
        base_price=3.0,
        min_price=1.0,
        is_active=True,
        is_visible=True,
    )
    session.add(merchant)
    session.add(category)
    session.commit()
    session.close()


def test_import_inventory_library_creates_rows_and_stats(tmp_path: Path):
    from services.inventory_service import import_inventory_library, list_inventory_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    payload = import_inventory_library(
        name="New Inventory",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=3.5,
        pick_price=0.8,
        delimiter="|",
        content="4111111111111111|12/30|123\n4111111111111111|12/30|123\nbad\n",
        push_ad=False,
        operator_username="admin",
        source_filename="inventory_upload.txt",
        session_factory=session_factory,
    )

    assert payload["result"]["total"] == 3
    assert payload["result"]["success"] == 1
    assert payload["result"]["duplicate"] == 1
    assert payload["result"]["invalid"] == 1

    rows = list_inventory_snapshot(session_factory=session_factory)
    assert len(rows) == 1
    assert rows[0]["name"] == "New Inventory"
    assert rows[0]["remaining"] == 1
    assert rows[0]["status"] == "active"


def test_inventory_library_price_status_delete_flow(tmp_path: Path):
    from services.inventory_service import (
        delete_inventory_library,
        import_inventory_library,
        list_inventory_snapshot,
        toggle_inventory_status,
        update_inventory_price,
    )

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    created = import_inventory_library(
        name="Price Change Inventory",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=2.0,
        pick_price=0.2,
        delimiter="|",
        content="4222222222222222|11/29|456",
        push_ad=False,
        operator_username="admin",
        source_filename="rows.txt",
        session_factory=session_factory,
    )
    inventory_id = int(created["library"]["id"])

    updated = update_inventory_price(
        inventory_id=inventory_id,
        unit_price=4.2,
        pick_price=1.2,
        session_factory=session_factory,
    )
    assert updated["unit_price"] == 4.2
    assert updated["pick_price"] == 1.2

    toggled = toggle_inventory_status(inventory_id=inventory_id, session_factory=session_factory)
    assert toggled["status"] == "inactive"

    delete_inventory_library(inventory_id=inventory_id, session_factory=session_factory)
    rows = list_inventory_snapshot(session_factory=session_factory)
    assert rows == []


def test_import_inventory_handles_existing_data_hash_rows(tmp_path: Path):
    from services.inventory_service import import_inventory_library
    from shared.models.category import Category
    from shared.models.inventory import InventoryLibrary
    from shared.models.merchant import Merchant
    from shared.models.product import ProductItem, ProductStatus
    from sqlmodel import select

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    session = session_factory()
    merchant = session.exec(select(Merchant).where(Merchant.name == PLATFORM_MERCHANT_NAME)).first()
    category = session.exec(select(Category).where(Category.name == DEFAULT_CATEGORY_NAME)).first()
    assert merchant is not None
    assert category is not None

    library = InventoryLibrary(
        name="Existing Inventory",
        merchant_id=int(merchant.id or 0),
        category_id=int(category.id or 0),
        unit_price=3,
        pick_price=1,
        status="active",
        total_count=1,
        sold_count=0,
        remaining_count=1,
    )
    session.add(library)
    session.commit()
    session.refresh(library)

    session.add(
        ProductItem(
            raw_data="4999999999999999|12/30|777",
            data_hash="existing-hash-row",
            bin_number="499999",
            category_id=int(category.id or 0),
            country_code="US",
            supplier_id=int(merchant.id or 0),
            inventory_library_id=int(library.id or 0),
            cost_price=1.0,
            selling_price=2.0,
            status=ProductStatus.AVAILABLE,
        )
    )
    session.commit()
    session.close()

    payload = import_inventory_library(
        name="Regression Import",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=3.5,
        pick_price=0.8,
        delimiter="|",
        content="4111111111111111|12/30|123",
        push_ad=False,
        operator_username="admin",
        source_filename="regression.txt",
        session_factory=session_factory,
    )

    assert payload["result"]["success"] == 1


def test_inventory_import_task_and_library_items_queries(tmp_path: Path):
    from services.inventory_service import (
        get_inventory_import_task_snapshot,
        import_inventory_library,
        list_inventory_library_items,
    )
    from shared.models.category import Category
    from shared.models.merchant import Merchant
    from sqlmodel import select

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    session = session_factory()
    merchant = session.exec(select(Merchant).order_by(Merchant.id.asc())).first()
    category = session.exec(select(Category).order_by(Category.id.asc())).first()
    session.close()
    assert merchant is not None
    assert category is not None

    payload = import_inventory_library(
        name="task-query-library",
        merchant_name=str(merchant.name),
        category_name=str(category.name),
        unit_price=5.2,
        pick_price=1.1,
        delimiter="|",
        content="4555555555555555|12/30|123\n4555555555555556|12/30|456",
        push_ad=False,
        operator_username="admin",
        source_filename="task-query.txt",
        session_factory=session_factory,
    )

    task_id = int(payload["task_id"])
    library_id = int(payload["library"]["id"])

    task = get_inventory_import_task_snapshot(task_id=task_id, session_factory=session_factory)
    assert task["id"] == task_id
    assert task["status"] == "completed"
    assert task["success"] == 2

    items = list_inventory_library_items(inventory_id=library_id, session_factory=session_factory)
    assert len(items) == 2
    assert items[0]["inventory_id"] == library_id


def test_import_inventory_library_extracts_country_code_from_fifth_field(tmp_path: Path):
    from services.inventory_service import import_inventory_library, list_inventory_library_items

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    payload = import_inventory_library(
        name="country-code-import",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=3.2,
        pick_price=1.1,
        delimiter="|",
        content="4003448188901441|09|28|888|US|Yoel Sanchez|7705 4th ave|New jersey|07047|2016814662|",
        push_ad=False,
        operator_username="admin",
        source_filename="country-code.txt",
        session_factory=session_factory,
    )

    library_id = int(payload["library"]["id"])
    items = list_inventory_library_items(inventory_id=library_id, session_factory=session_factory)
    assert len(items) == 1
    assert items[0]["country_code"] == "US"


def test_toggle_inventory_status_updates_product_item_lock_fields(tmp_path: Path):
    from services.inventory_service import (
        import_inventory_library,
        toggle_inventory_status,
    )
    from shared.models.admin_user import AdminUser
    from shared.models.product import ProductItem, ProductStatus
    from sqlmodel import select

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    created = import_inventory_library(
        name="lock-flow-library",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=5.0,
        pick_price=2.0,
        delimiter="|",
        content="4222222222222222|11|29|456|US",
        push_ad=False,
        operator_username="admin",
        source_filename="lock-flow.txt",
        session_factory=session_factory,
    )
    inventory_id = int(created["library"]["id"])

    toggled = toggle_inventory_status(inventory_id=inventory_id, session_factory=session_factory)
    assert toggled["status"] == "inactive"

    session = session_factory()
    admin = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert admin is not None
    item = session.exec(
        select(ProductItem).where(ProductItem.inventory_library_id == inventory_id)
    ).first()
    assert item is not None
    assert item.status == ProductStatus.LOCKED
    assert item.locked_by_user_id == int(admin.id or 0)
    assert item.locked_at is not None
    assert item.lock_expires_at is not None
    session.close()

    toggled_back = toggle_inventory_status(inventory_id=inventory_id, session_factory=session_factory)
    assert toggled_back["status"] == "active"

    session = session_factory()
    item = session.exec(
        select(ProductItem).where(ProductItem.inventory_library_id == inventory_id)
    ).first()
    assert item is not None
    assert item.status == ProductStatus.AVAILABLE
    assert item.locked_by_user_id is None
    assert item.locked_at is None
    assert item.lock_expires_at is None
    session.close()


def test_update_inventory_price_syncs_available_product_items(tmp_path: Path):
    from services.inventory_service import (
        import_inventory_library,
        update_inventory_price,
    )
    from shared.models.product import ProductItem, ProductStatus
    from sqlmodel import select

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    created = import_inventory_library(
        name="price-sync-library",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=3.5,
        pick_price=0.8,
        delimiter="|",
        content="4555555555555555|12|30|123|US\n4666666666666666|10|29|456|CA",
        push_ad=False,
        operator_username="admin",
        source_filename="price-sync.txt",
        session_factory=session_factory,
    )
    inventory_id = int(created["library"]["id"])

    update_inventory_price(
        inventory_id=inventory_id,
        unit_price=8.88,
        pick_price=4.44,
        session_factory=session_factory,
    )

    session = session_factory()
    rows = list(
        session.exec(
            select(ProductItem).where(ProductItem.inventory_library_id == inventory_id)
        ).all()
    )
    assert len(rows) == 2
    assert all(item.status == ProductStatus.AVAILABLE for item in rows)
    assert all(round(float(item.selling_price or 0), 2) == 8.88 for item in rows)
    assert all(round(float(item.cost_price or 0), 2) == 4.44 for item in rows)
    session.close()


def test_list_inventory_filter_options_returns_fixed_category_set(tmp_path: Path):
    from services.inventory_service import list_inventory_filter_options

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    options = list_inventory_filter_options(session_factory=session_factory)
    assert options["category_names"] == [
        "全资库 一手",
        "全资库 二手",
        "裸资库",
        "特价库",
    ]
