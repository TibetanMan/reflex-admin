from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminUser
from shared.models.merchant import Merchant


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "merchant_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def test_create_list_update_toggle_merchant_flow(tmp_path: Path):
    from services.merchant_service import (
        create_merchant_record,
        list_merchants_snapshot,
        toggle_merchant_featured,
        toggle_merchant_status,
        toggle_merchant_verified,
        update_merchant_record,
    )

    session_factory = _session_factory(tmp_path)
    created = create_merchant_record(
        name="Merchant A",
        description="merchant-a",
        contact_telegram="@merchant_a",
        contact_email="merchant-a@example.com",
        fee_rate=0.06,
        usdt_address="TRX_MERCHANT_A",
        is_featured=False,
        session_factory=session_factory,
    )
    assert created["name"] == "Merchant A"
    assert created["fee_rate_label"] == "6.00%"

    rows = list_merchants_snapshot(session_factory=session_factory)
    assert len(rows) == 1
    assert rows[0]["name"] == "Merchant A"

    updated = update_merchant_record(
        merchant_id=int(created["id"]),
        name="Merchant A+",
        description="merchant-a-plus",
        contact_telegram="@merchant_aplus",
        contact_email="merchant-a-plus@example.com",
        fee_rate=0.08,
        usdt_address="TRX_MERCHANT_A_PLUS",
        is_verified=True,
        is_featured=True,
        session_factory=session_factory,
    )
    assert updated["name"] == "Merchant A+"
    assert updated["is_verified"] is True
    assert updated["is_featured"] is True
    assert updated["fee_rate_label"] == "8.00%"

    s1 = toggle_merchant_status(merchant_id=int(created["id"]), session_factory=session_factory)
    s2 = toggle_merchant_featured(merchant_id=int(created["id"]), session_factory=session_factory)
    s3 = toggle_merchant_verified(merchant_id=int(created["id"]), session_factory=session_factory)
    assert isinstance(s1["is_active"], bool)
    assert isinstance(s2["is_featured"], bool)
    assert isinstance(s3["is_verified"], bool)

    session = session_factory()
    assert session.exec(select(Merchant)).first() is not None
    assert session.exec(select(AdminUser)).first() is not None
    session.close()


def test_get_merchant_snapshot_returns_single_row(tmp_path: Path):
    from services.merchant_service import create_merchant_record, get_merchant_snapshot

    session_factory = _session_factory(tmp_path)
    created = create_merchant_record(
        name="Merchant Detail",
        description="merchant detail row",
        contact_telegram="@merchant_detail",
        contact_email="merchant-detail@example.com",
        fee_rate=0.05,
        usdt_address="TRX_MERCHANT_DETAIL",
        is_featured=False,
        session_factory=session_factory,
    )

    row = get_merchant_snapshot(merchant_id=int(created["id"]), session_factory=session_factory)
    assert row["id"] == int(created["id"])
    assert row["name"] == "Merchant Detail"
