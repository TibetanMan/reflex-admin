"""DB services for system settings page."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from services.wallet_config_sync import sync_default_wallet_from_settings
from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.system_setting import SystemSetting


DEFAULT_USDT_ADDRESS = "TDEFAULTUSDTADDRESS000000000000"
DEFAULT_USDT_QUERY_API = {
    "api_url": "https://apilist.tronscanapi.com/api/transfer/trc20",
    "api_key": "",
    "timeout_seconds": 8,
    "trc20_id": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
}
DEFAULT_BINS_QUERY_API = {
    "api_url": "https://api.example.com/bins/query",
    "api_key": "",
    "timeout_seconds": 8,
}
DEFAULT_TELEGRAM_PUSH = {
    "enabled": True,
    "bot_token": "",
    "chat_id": "",
    "push_interval_seconds": 5,
    "max_messages_per_minute": 30,
    "retry_times": 3,
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _json_load_dict(value: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(value or "{}")
    except json.JSONDecodeError:
        return dict(fallback)
    if not isinstance(data, dict):
        return dict(fallback)
    merged = dict(fallback)
    merged.update(data)
    return merged


def _resolve_operator(session: Session, username: str) -> Optional[AdminUser]:
    text = str(username or "").strip()
    if not text:
        return None
    return session.exec(select(AdminUser).where(AdminUser.username == text)).first()


def _upsert_setting(
    *,
    session: Session,
    key: str,
    payload: dict[str, Any],
    operator_id: Optional[int],
) -> None:
    row = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if row is None:
        row = SystemSetting(
            key=key,
            value_json="{}",
        )
    row.value_json = json.dumps(payload, ensure_ascii=False)
    row.updated_by = operator_id
    row.updated_at = _now()
    session.add(row)


def _write_audit(
    *,
    session: Session,
    operator_id: Optional[int],
    action: str,
    detail: dict[str, Any],
) -> None:
    session.add(
        AdminAuditLog(
            operator_id=operator_id,
            action=action,
            target_type="system_setting",
            target_id=None,
            request_id=f"{action}-{datetime.now():%Y%m%d%H%M%S%f}",
            detail_json=json.dumps(detail, ensure_ascii=False),
        )
    )


def _get_setting_payload(
    *,
    session: Session,
    key: str,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    row = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if row is None:
        return dict(fallback)
    return _json_load_dict(str(row.value_json or "{}"), fallback)


def get_settings_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        default_usdt_payload = _get_setting_payload(
            session=session,
            key="settings.default_usdt_address",
            fallback={"value": DEFAULT_USDT_ADDRESS},
        )
        usdt_payload = _get_setting_payload(
            session=session,
            key="settings.usdt_query_api",
            fallback=DEFAULT_USDT_QUERY_API,
        )
        bins_payload = _get_setting_payload(
            session=session,
            key="settings.bins_query_api",
            fallback=DEFAULT_BINS_QUERY_API,
        )
        tg_payload = _get_setting_payload(
            session=session,
            key="settings.telegram_push",
            fallback=DEFAULT_TELEGRAM_PUSH,
        )

        return {
            "default_usdt_address": str(default_usdt_payload.get("value") or DEFAULT_USDT_ADDRESS),
            "usdt_query_api_url": str(usdt_payload.get("api_url") or DEFAULT_USDT_QUERY_API["api_url"]),
            "usdt_query_api_key": str(usdt_payload.get("api_key") or ""),
            "usdt_query_api_timeout_seconds": int(
                usdt_payload.get("timeout_seconds") or DEFAULT_USDT_QUERY_API["timeout_seconds"]
            ),
            "bins_query_api_url": str(bins_payload.get("api_url") or DEFAULT_BINS_QUERY_API["api_url"]),
            "bins_query_api_key": str(bins_payload.get("api_key") or ""),
            "bins_query_api_timeout_seconds": int(
                bins_payload.get("timeout_seconds") or DEFAULT_BINS_QUERY_API["timeout_seconds"]
            ),
            "telegram_push_enabled": bool(
                tg_payload.get("enabled", DEFAULT_TELEGRAM_PUSH["enabled"])
            ),
            "telegram_bot_token": str(tg_payload.get("bot_token") or ""),
            "telegram_chat_id": str(tg_payload.get("chat_id") or ""),
            "telegram_push_interval_seconds": int(
                tg_payload.get("push_interval_seconds")
                or DEFAULT_TELEGRAM_PUSH["push_interval_seconds"]
            ),
            "telegram_max_messages_per_minute": int(
                tg_payload.get("max_messages_per_minute")
                or DEFAULT_TELEGRAM_PUSH["max_messages_per_minute"]
            ),
            "telegram_retry_times": int(
                tg_payload.get("retry_times") or DEFAULT_TELEGRAM_PUSH["retry_times"]
            ),
        }
    finally:
        session.close()


def update_default_usdt_address(
    *,
    address: str,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    address_text = str(address or "").strip()
    if not address_text:
        raise ValueError("Default USDT address is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        operator = _resolve_operator(session, operator_username)
        operator_id = int(operator.id or 0) if operator else None
        _upsert_setting(
            session=session,
            key="settings.default_usdt_address",
            payload={"value": address_text},
            operator_id=operator_id,
        )
        sync_default_wallet_from_settings(session)
        _write_audit(
            session=session,
            operator_id=operator_id,
            action="settings.default_usdt.update",
            detail={"value": address_text},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return get_settings_snapshot(session_factory=session_factory)


def update_usdt_query_api_settings(
    *,
    api_url: str,
    api_key: str,
    timeout_seconds: int,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    url_text = str(api_url or "").strip()
    if not url_text:
        raise ValueError("USDT query API URL is required.")

    timeout = max(1, min(60, int(timeout_seconds)))

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        operator = _resolve_operator(session, operator_username)
        operator_id = int(operator.id or 0) if operator else None
        payload = {
            "api_url": url_text,
            "api_key": str(api_key or "").strip(),
            "timeout_seconds": timeout,
        }
        _upsert_setting(
            session=session,
            key="settings.usdt_query_api",
            payload=payload,
            operator_id=operator_id,
        )
        _write_audit(
            session=session,
            operator_id=operator_id,
            action="settings.usdt_query_api.update",
            detail=payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return get_settings_snapshot(session_factory=session_factory)


def update_bins_query_api_settings(
    *,
    api_url: str,
    api_key: str,
    timeout_seconds: int,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    url_text = str(api_url or "").strip()
    if not url_text:
        raise ValueError("BINS query API URL is required.")

    timeout = max(1, min(60, int(timeout_seconds)))

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        operator = _resolve_operator(session, operator_username)
        operator_id = int(operator.id or 0) if operator else None
        payload = {
            "api_url": url_text,
            "api_key": str(api_key or "").strip(),
            "timeout_seconds": timeout,
        }
        _upsert_setting(
            session=session,
            key="settings.bins_query_api",
            payload=payload,
            operator_id=operator_id,
        )
        _write_audit(
            session=session,
            operator_id=operator_id,
            action="settings.bins_query_api.update",
            detail=payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return get_settings_snapshot(session_factory=session_factory)


def update_telegram_push_settings(
    *,
    enabled: bool,
    bot_token: str,
    chat_id: str,
    push_interval_seconds: int,
    max_messages_per_minute: int,
    retry_times: int,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    payload = {
        "enabled": bool(enabled),
        "bot_token": str(bot_token or "").strip(),
        "chat_id": str(chat_id or "").strip(),
        "push_interval_seconds": max(1, min(120, int(push_interval_seconds))),
        "max_messages_per_minute": max(1, min(300, int(max_messages_per_minute))),
        "retry_times": max(0, min(10, int(retry_times))),
    }

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        operator = _resolve_operator(session, operator_username)
        operator_id = int(operator.id or 0) if operator else None
        _upsert_setting(
            session=session,
            key="settings.telegram_push",
            payload=payload,
            operator_id=operator_id,
        )
        _write_audit(
            session=session,
            operator_id=operator_id,
            action="settings.telegram_push.update",
            detail=payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return get_settings_snapshot(session_factory=session_factory)
