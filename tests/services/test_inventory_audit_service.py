from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.category import Category, CategoryType
from shared.models.merchant import Merchant

PLATFORM_MERCHANT_NAME = "\u5e73\u53f0\u81ea\u8425"
DEFAULT_CATEGORY_NAME = "\u5168\u8d44\u5e93 \u4e00\u624b"


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "inventory_audit.db"
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

    session.add(
        Merchant(
            admin_user_id=int(merchant_admin.id or 0),
            name=PLATFORM_MERCHANT_NAME,
            is_active=True,
            is_verified=True,
        )
    )
    session.add(
        Category(
            name=DEFAULT_CATEGORY_NAME,
            code="inventory_cat_1",
            type=CategoryType.POOL,
            base_price=3.0,
            min_price=1.0,
            is_active=True,
            is_visible=True,
        )
    )
    session.commit()
    session.close()


def test_inventory_import_update_delete_write_admin_audit_logs(tmp_path: Path):
    from services.inventory_service import (
        delete_inventory_library,
        import_inventory_library,
        update_inventory_price,
    )

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    created = import_inventory_library(
        name="audit-library",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=3.2,
        pick_price=1.1,
        delimiter="|",
        content="4003448188901441|09|28|888|US",
        push_ad=False,
        operator_username="admin",
        source_filename="audit-import.txt",
        session_factory=session_factory,
    )
    inventory_id = int(created["library"]["id"])

    update_inventory_price(
        inventory_id=inventory_id,
        unit_price=8.5,
        pick_price=2.5,
        operator_username="admin",
        session_factory=session_factory,
    )
    delete_inventory_library(
        inventory_id=inventory_id,
        operator_username="admin",
        session_factory=session_factory,
    )

    session = session_factory()
    admin = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert admin is not None
    rows = list(session.exec(select(AdminAuditLog).order_by(AdminAuditLog.id.asc())).all())
    actions = [str(item.action) for item in rows]
    assert "inventory.import" in actions
    assert "inventory.update_price" in actions
    assert "inventory.delete_library" in actions

    target_rows = [item for item in rows if int(item.target_id or 0) == inventory_id]
    assert target_rows
    assert all(int(item.operator_id or 0) == int(admin.id or 0) for item in target_rows)
    session.close()


def test_inventory_toggle_status_writes_admin_audit_log(tmp_path: Path):
    from services.inventory_service import (
        import_inventory_library,
        toggle_inventory_status,
    )

    session_factory = _session_factory(tmp_path)
    _seed_base_rows(session_factory)

    created = import_inventory_library(
        name="audit-toggle-library",
        merchant_name=PLATFORM_MERCHANT_NAME,
        category_name=DEFAULT_CATEGORY_NAME,
        unit_price=5.5,
        pick_price=2.2,
        delimiter="|",
        content="4222222222222222|11|29|456|US",
        push_ad=False,
        operator_username="admin",
        source_filename="audit-toggle.txt",
        session_factory=session_factory,
    )
    inventory_id = int(created["library"]["id"])

    toggle_inventory_status(
        inventory_id=inventory_id,
        operator_username="admin",
        session_factory=session_factory,
    )
    toggle_inventory_status(
        inventory_id=inventory_id,
        operator_username="admin",
        session_factory=session_factory,
    )

    session = session_factory()
    admin = session.exec(select(AdminUser).where(AdminUser.username == "admin")).first()
    assert admin is not None
    rows = list(
        session.exec(
            select(AdminAuditLog)
            .where(AdminAuditLog.action == "inventory.toggle_status")
            .where(AdminAuditLog.target_id == inventory_id)
            .order_by(AdminAuditLog.id.asc())
        ).all()
    )
    assert len(rows) == 2
    assert all(int(item.operator_id or 0) == int(admin.id or 0) for item in rows)
    assert "inactive" in str(rows[0].detail_json)
    assert "active" in str(rows[1].detail_json)
    session.close()
