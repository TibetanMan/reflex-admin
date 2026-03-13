"""Admin account lifecycle services with strict super-admin control."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser


def _generate_secure_initial_password() -> str:
    token = secrets.token_urlsafe(12)
    return f"Admin-{token}-A1!"


def _parse_admin_role(value: str | AdminRole) -> AdminRole:
    if isinstance(value, AdminRole):
        return value
    text = str(value or "").strip().lower()
    if text == AdminRole.SUPER_ADMIN.value:
        return AdminRole.SUPER_ADMIN
    if text == AdminRole.AGENT.value:
        return AdminRole.AGENT
    if text == AdminRole.MERCHANT.value:
        return AdminRole.MERCHANT
    raise ValueError("Unsupported admin role.")


def _get_admin_by_username(session: Session, username: str) -> Optional[AdminUser]:
    return session.exec(
        select(AdminUser).where(AdminUser.username == str(username or "").strip())
    ).first()


def create_admin_account(
    *,
    actor_username: str,
    username: str,
    display_name: str,
    role: str | AdminRole,
    email: str = "",
    initial_password: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    """Create managed admin account. Only active super-admin can call this."""
    actor_text = str(actor_username or "").strip()
    username_text = str(username or "").strip()
    display_name_text = str(display_name or "").strip()
    if not actor_text:
        raise PermissionError("Active super admin is required.")
    if not username_text:
        raise ValueError("Username is required.")
    if not display_name_text:
        raise ValueError("Display name is required.")

    role_enum = _parse_admin_role(role)
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        actor = _get_admin_by_username(session, actor_text)
        if actor is None or not bool(actor.is_active) or actor.role != AdminRole.SUPER_ADMIN:
            raise PermissionError("Only active super admin can create admin account.")

        if _get_admin_by_username(session, username_text) is not None:
            raise ValueError("Admin username already exists.")

        seed_password = str(initial_password or "").strip() or _generate_secure_initial_password()
        account = AdminUser(
            username=username_text,
            email=str(email or "").strip() or f"{username_text}@local.test",
            password_hash="",
            role=role_enum,
            display_name=display_name_text,
            is_active=True,
            is_verified=True,
        )
        account.set_password(seed_password)
        account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(account)
        session.commit()
        session.refresh(account)

        session.add(
            AdminAuditLog(
                operator_id=int(actor.id or 0),
                action="admin.account.create",
                target_type="admin_user",
                target_id=int(account.id or 0),
                detail_json=json.dumps(
                    {
                        "username": account.username,
                        "role": role_enum.value,
                        "created_by": actor.username,
                    },
                    ensure_ascii=False,
                ),
            )
        )
        session.commit()

        return {
            "id": int(account.id or 0),
            "username": account.username,
            "display_name": account.display_name,
            "email": str(account.email or ""),
            "role": role_enum.value,
            "is_active": bool(account.is_active),
            "initial_password": seed_password,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
