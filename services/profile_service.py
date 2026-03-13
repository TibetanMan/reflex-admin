"""DB services for profile page."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_user import AdminUser


def _to_text(value: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    return value.strftime(fmt)


def _row_to_snapshot(row: AdminUser) -> dict[str, Any]:
    return {
        "id": int(row.id or 0),
        "username": str(row.username),
        "display_name": str(row.display_name or row.username),
        "email": str(row.email or ""),
        "phone": str(row.phone or ""),
        "avatar_url": str(row.avatar_url or ""),
        "role": str(row.role.value if hasattr(row.role, "value") else row.role),
        "is_active": bool(row.is_active),
        "created_at": _to_text(row.created_at, "%Y-%m-%d"),
        "last_login_at": _to_text(row.last_login_at, "%Y-%m-%d %H:%M"),
    }


def _pick_user(session: Session, username: str = "") -> Optional[AdminUser]:
    username_text = str(username or "").strip()
    if not username_text:
        return None
    return session.exec(select(AdminUser).where(AdminUser.username == username_text)).first()


def get_profile_snapshot(
    *,
    username: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    username_text = str(username or "").strip()
    if not username_text:
        raise ValueError("Profile username is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = _pick_user(session, username=username_text)
        if row is None:
            raise ValueError("Admin user not found.")
        return _row_to_snapshot(row)
    finally:
        session.close()


def update_profile_snapshot(
    *,
    username: str,
    display_name: str,
    email: str,
    phone: str,
    avatar_url: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    username_text = str(username or "").strip()
    if not username_text:
        raise ValueError("Profile username is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = _pick_user(session, username=username_text)
        if row is None:
            raise ValueError("Admin user not found.")

        display_name_text = str(display_name or "").strip()
        if not display_name_text:
            raise ValueError("Display name is required.")

        row.display_name = display_name_text
        row.email = str(email or "").strip() or None
        row.phone = str(phone or "").strip() or None
        row.avatar_url = str(avatar_url or "").strip() or None
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_snapshot(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_profile_password(
    *,
    username: str,
    old_password: str,
    new_password: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    username_text = str(username or "").strip()
    if not username_text:
        raise ValueError("Profile username is required.")

    old_text = str(old_password or "")
    new_text = str(new_password or "")
    if not old_text:
        raise ValueError("Current password is required.")
    if not new_text:
        raise ValueError("New password is required.")
    if old_text == new_text:
        raise ValueError("New password must be different from current password.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = _pick_user(session, username=username_text)
        if row is None:
            raise ValueError("Admin user not found.")
        if not row.verify_password(old_text):
            raise ValueError("Current password is incorrect.")

        row.set_password(new_text)
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"ok": True, "username": str(row.username)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
