"""Authentication service backed by SQLModel sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_user import AdminUser


def _build_auth_user_payload(user: AdminUser) -> dict[str, Any]:
    return {
        "id": int(user.id or 0),
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "avatar_url": str(user.avatar_url or ""),
        "is_active": bool(user.is_active),
    }


def get_admin_profile(
    username: str,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> Optional[dict[str, Any]]:
    """Fetch active admin profile by username."""
    username_text = str(username or "").strip()
    if not username_text:
        return None

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = session.exec(select(AdminUser).where(AdminUser.username == username_text)).first()
        if user is None or not user.is_active:
            return None
        return _build_auth_user_payload(user)
    finally:
        session.close()


def refresh_admin_session(
    username: str,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> Optional[dict[str, Any]]:
    """Refresh auth session payload for an active admin user."""
    user_payload = get_admin_profile(username, session_factory=session_factory)
    if user_payload is None:
        return None

    user_id = int(user_payload.get("id") or 0)
    epoch_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "access_token": f"access-{user_id}-{epoch_ms}",
        "refresh_token": f"refresh-{user_id}-{epoch_ms}",
        "user": user_payload,
    }


def logout_admin(username: str = "") -> dict[str, Any]:
    """Return logout acknowledgement payload."""
    return {
        "ok": True,
        "username": str(username or "").strip(),
    }


def authenticate_admin(
    username: str,
    password: str,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> Optional[dict[str, Any]]:
    """Validate admin credentials and return normalized auth payload."""
    username_text = str(username or "").strip()
    password_text = str(password or "")
    if not username_text or not password_text:
        return None

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = session.exec(select(AdminUser).where(AdminUser.username == username_text)).first()
        if user is None or not user.is_active:
            return None
        if not user.verify_password(password_text):
            return None

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user.last_login_at = now
        user.updated_at = now
        session.add(user)
        session.commit()
        session.refresh(user)

        return _build_auth_user_payload(user)
    finally:
        session.close()
