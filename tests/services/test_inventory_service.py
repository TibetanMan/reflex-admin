from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.category import INVENTORY_FIXED_CATEGORY_NAMES
from shared.models.inventory import InventoryImportTask, InventoryLibrary
from shared.models.merchant import Merchant
from shared.models.product import ProductItem, ProductStatus


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "inventory_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_inventory_rows(session_factory):
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

        session.add(
            Merchant(
                admin_user_id=int(admin.id or 0),
                name="平台自营",
                is_active=True,
                is_verified=True,
            )
        )
        session.commit()
    finally:
        session.close()


def test_append_inventory_library_items_reuses_existing_library_row(tmp_path: Path):
    from services.inventory_service import (
        append_inventory_library_items,
        import_inventory_library,
    )

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]

    created = import_inventory_library(
        name="Main Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=20.0,
        pick_price=10.0,
        delimiter="|",
        content="4111111111111111|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )
    library_id = int(created["library"]["id"])

    appended = append_inventory_library_items(
        inventory_id=library_id,
        delimiter="|",
        content="5555555555554444|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="append.txt",
        session_factory=session_factory,
    )

    assert int(appended["library"]["id"]) == library_id

    session = session_factory()
    try:
        library_rows = list(session.exec(select(InventoryLibrary)).all())
        task_rows = list(
            session.exec(
                select(InventoryImportTask).where(InventoryImportTask.library_id == library_id)
            ).all()
        )
    finally:
        session.close()

    assert len(library_rows) == 1
    assert len(task_rows) == 2


def test_append_inventory_library_items_refreshes_counts(tmp_path: Path):
    from services.inventory_service import (
        append_inventory_library_items,
        import_inventory_library,
    )

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]

    created = import_inventory_library(
        name="Count Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=18.0,
        pick_price=8.0,
        delimiter="|",
        content="4242424242424242|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )
    library_id = int(created["library"]["id"])

    appended = append_inventory_library_items(
        inventory_id=library_id,
        delimiter="|",
        content="\n".join(
            [
                "5555555555554444|12|2030|123|US",
                "abc|12|2030|123|US",
            ]
        ),
        push_ad=False,
        operator_username="admin",
        source_filename="append-counts.txt",
        session_factory=session_factory,
    )

    assert appended["result"] == {"total": 2, "success": 1, "duplicate": 0, "invalid": 1}
    assert int(appended["library"]["total"]) == 2
    assert int(appended["library"]["remaining"]) == 2
    assert int(appended["library"]["sold"]) == 0

    session = session_factory()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.name == "平台自营")).first()
    finally:
        session.close()

    assert merchant is not None
    assert merchant.total_products == 2


def test_import_inventory_library_updates_merchant_total_products(tmp_path: Path):
    from services.inventory_service import import_inventory_library

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]

    import_inventory_library(
        name="Merchant Aggregate Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=12.0,
        pick_price=6.0,
        delimiter="|",
        content="\n".join(
            [
                "4111111111111111|12|2030|123|US",
                "5555555555554444|12|2030|123|US",
            ]
        ),
        push_ad=False,
        operator_username="admin",
        source_filename="merchant-aggregate.txt",
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.name == "平台自营")).first()
    finally:
        session.close()

    assert merchant is not None
    assert merchant.total_products == 2


def test_append_inventory_library_items_preserves_duplicate_rules(tmp_path: Path):
    from services.inventory_service import (
        append_inventory_library_items,
        import_inventory_library,
    )

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]

    created = import_inventory_library(
        name="Dup Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=15.0,
        pick_price=6.0,
        delimiter="|",
        content="4111111111111111|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )
    library_id = int(created["library"]["id"])

    appended = append_inventory_library_items(
        inventory_id=library_id,
        delimiter="|",
        content="\n".join(
            [
                "4111111111111111|12|2030|123|US",
                "4111111111111111|12|2030|123|US",
                "5555555555554444|12|2030|123|US",
            ]
        ),
        push_ad=False,
        operator_username="admin",
        source_filename="append-dup.txt",
        session_factory=session_factory,
    )

    assert appended["result"] == {"total": 3, "success": 1, "duplicate": 2, "invalid": 0}
    assert int(appended["library"]["total"]) == 2

    session = session_factory()
    try:
        product_rows = list(
            session.exec(
                select(ProductItem).where(ProductItem.inventory_library_id == library_id)
            ).all()
        )
    finally:
        session.close()

    assert len(product_rows) == 2


def test_import_and_append_push_review_use_live_merchant_name(tmp_path: Path, monkeypatch) -> None:
    from services.inventory_service import (
        append_inventory_library_items,
        import_inventory_library,
    )

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]
    review_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "services.inventory_service.register_inventory_review_task",
        lambda **kwargs: review_calls.append(kwargs),
    )

    created = import_inventory_library(
        name="Push Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=11.0,
        pick_price=5.5,
        delimiter="|",
        content="4111111111111111|12|2030|123|US",
        push_ad=True,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )
    library_id = int(created["library"]["id"])

    appended = append_inventory_library_items(
        inventory_id=library_id,
        delimiter="|",
        content="5555555555554444|12|2030|123|US",
        push_ad=True,
        operator_username="admin",
        source_filename="append.txt",
        session_factory=session_factory,
    )

    assert int(appended["library"]["id"]) == library_id
    assert review_calls == [
        {
            "inventory_id": library_id,
            "inventory_name": "Push Library",
            "merchant_name": "平台自营",
            "source": "inventory_import",
        },
        {
            "inventory_id": library_id,
            "inventory_name": "Push Library",
            "merchant_name": "平台自营",
            "source": "inventory_import",
        },
    ]


def test_append_inventory_library_items_keeps_inactive_library_items_locked(tmp_path: Path) -> None:
    from services.inventory_service import (
        append_inventory_library_items,
        import_inventory_library,
        toggle_inventory_status,
    )

    session_factory = _session_factory(tmp_path)
    _seed_inventory_rows(session_factory)
    category_name = INVENTORY_FIXED_CATEGORY_NAMES[0]

    created = import_inventory_library(
        name="Inactive Library",
        merchant_name="平台自营",
        category_name=category_name,
        unit_price=17.0,
        pick_price=7.0,
        delimiter="|",
        content="4111111111111111|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="seed.txt",
        session_factory=session_factory,
    )
    library_id = int(created["library"]["id"])

    toggled = toggle_inventory_status(
        inventory_id=library_id,
        operator_username="admin",
        session_factory=session_factory,
    )
    appended = append_inventory_library_items(
        inventory_id=library_id,
        delimiter="|",
        content="5555555555554444|12|2030|123|US",
        push_ad=False,
        operator_username="admin",
        source_filename="append.txt",
        session_factory=session_factory,
    )

    assert toggled["status"] == "inactive"
    assert appended["library"]["status"] == "inactive"

    session = session_factory()
    try:
        product_rows = list(
            session.exec(
                select(ProductItem).where(ProductItem.inventory_library_id == library_id)
            ).all()
        )
    finally:
        session.close()

    assert len(product_rows) == 2
    assert [row.status for row in product_rows] == [ProductStatus.LOCKED, ProductStatus.LOCKED]
