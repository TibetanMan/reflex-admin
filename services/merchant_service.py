"""DB services for merchant management page."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.merchant import Merchant


def _format_fee(rate: float) -> str:
    return f"{float(rate) * 100:.2f}%"


def _admin_username_base(name: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(name or "").lower()).strip("_")
    return text or "merchant"


def _ensure_unique_admin_identity(session: Session, base: str) -> tuple[str, str]:
    username = base
    email = f"{username}@local.test"
    i = 1
    while session.exec(select(AdminUser).where(AdminUser.username == username)).first() is not None:
        i += 1
        username = f"{base}_{i}"
        email = f"{username}@local.test"
    return username, email


def _to_row(merchant: Merchant) -> dict[str, Any]:
    return {
        "id": int(merchant.id or 0),
        "name": str(merchant.name),
        "description": str(merchant.description or ""),
        "contact_telegram": str(merchant.contact_telegram or ""),
        "contact_email": str(merchant.contact_email or ""),
        "fee_rate": float(merchant.fee_rate or 0),
        "fee_rate_label": _format_fee(float(merchant.fee_rate or 0)),
        "usdt_address": str(merchant.usdt_address or ""),
        "is_active": bool(merchant.is_active),
        "is_verified": bool(merchant.is_verified),
        "is_featured": bool(merchant.is_featured),
        "total_products": int(merchant.total_products or 0),
        "sold_products": int(merchant.sold_products or 0),
        "total_sales": float(merchant.total_sales or 0),
        "balance": float(merchant.balance or 0),
        "frozen_balance": float(merchant.frozen_balance or 0),
        "rating": float(merchant.rating or 0),
        "created_at": merchant.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def list_merchants_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(session.exec(select(Merchant).order_by(Merchant.created_at.desc())).all())
        return [_to_row(item) for item in rows]
    finally:
        session.close()


def get_merchant_snapshot(
    *,
    merchant_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(merchant_id):
            return row
    raise ValueError("Merchant not found.")


def create_merchant_record(
    *,
    name: str,
    description: str,
    contact_telegram: str,
    contact_email: str,
    fee_rate: float,
    usdt_address: str,
    is_featured: bool,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    if not name_text:
        raise ValueError("Merchant name is required.")

    rate = float(fee_rate)
    if rate < 0 or rate > 1:
        raise ValueError("Fee rate must be between 0 and 1.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        base = _admin_username_base(name_text)
        username, email = _ensure_unique_admin_identity(session, base)
        admin = AdminUser(
            username=username,
            email=email,
            password_hash="",
            role=AdminRole.MERCHANT,
            display_name=name_text,
            is_active=True,
            is_verified=True,
        )
        admin.set_password("merchant123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        merchant = Merchant(
            admin_user_id=int(admin.id or 0),
            name=name_text,
            description=str(description or "").strip() or None,
            contact_telegram=str(contact_telegram or "").strip() or None,
            contact_email=str(contact_email or "").strip() or None,
            fee_rate=rate,
            usdt_address=str(usdt_address or "").strip() or None,
            is_active=True,
            is_verified=False,
            is_featured=bool(is_featured),
            total_products=0,
            sold_products=0,
            total_sales=0,
            balance=0,
            frozen_balance=0,
            rating=5.0,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(merchant.id or 0):
            return row
    raise ValueError("Created merchant not found in snapshot.")


def update_merchant_record(
    *,
    merchant_id: int,
    name: str,
    description: str,
    contact_telegram: str,
    contact_email: str,
    fee_rate: float,
    usdt_address: str,
    is_verified: bool,
    is_featured: bool,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    if not name_text:
        raise ValueError("Merchant name is required.")
    rate = float(fee_rate)
    if rate < 0 or rate > 1:
        raise ValueError("Fee rate must be between 0 and 1.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
        if merchant is None:
            raise ValueError("Merchant not found.")
        merchant.name = name_text
        merchant.description = str(description or "").strip() or None
        merchant.contact_telegram = str(contact_telegram or "").strip() or None
        merchant.contact_email = str(contact_email or "").strip() or None
        merchant.fee_rate = rate
        merchant.usdt_address = str(usdt_address or "").strip() or None
        merchant.is_verified = bool(is_verified)
        merchant.is_featured = bool(is_featured)
        merchant.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(merchant)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(merchant_id):
            return row
    raise ValueError("Updated merchant not found in snapshot.")


def toggle_merchant_status(
    *,
    merchant_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
        if merchant is None:
            raise ValueError("Merchant not found.")
        merchant.is_active = not bool(merchant.is_active)
        merchant.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(merchant)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(merchant_id):
            return row
    raise ValueError("Toggled merchant not found in snapshot.")


def toggle_merchant_featured(
    *,
    merchant_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
        if merchant is None:
            raise ValueError("Merchant not found.")
        merchant.is_featured = not bool(merchant.is_featured)
        merchant.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(merchant)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(merchant_id):
            return row
    raise ValueError("Toggled merchant not found in snapshot.")


def toggle_merchant_verified(
    *,
    merchant_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
        if merchant is None:
            raise ValueError("Merchant not found.")
        merchant.is_verified = not bool(merchant.is_verified)
        merchant.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(merchant)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_merchants_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(merchant_id):
            return row
    raise ValueError("Toggled merchant not found in snapshot.")
