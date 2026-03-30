"""Services for agent campaign configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_user import AdminUser
from shared.models.agent import Agent
from shared.models.agent_campaign import AgentCampaignConfig
from shared.models.bot_instance import BotInstance


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("T", " ")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Invalid datetime value.") from exc


def _parse_decimal(value: Any, *, default: str) -> Decimal:
    raw = default if value in (None, "") else str(value).strip()
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid decimal value.") from exc


def _format_decimal_plain(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def campaign_status_text(row: AgentCampaignConfig, *, now: datetime) -> str:
    if not row.is_enabled:
        return "disabled"
    if row.starts_at and now < row.starts_at:
        return "upcoming"
    if row.ends_at and now > row.ends_at:
        return "expired"
    return "active"


def _campaign_summary_text(row: AgentCampaignConfig) -> str:
    rate_percent = Decimal(str(row.first_deposit_bonus_rate or 0)) * Decimal("100")
    fixed_amount = Decimal(str(row.first_deposit_bonus_amount or 0))
    return f"首次充值赠送 {_format_decimal_plain(rate_percent)}% + {_format_decimal_plain(fixed_amount)} USDT"


def _row_to_payload(row: AgentCampaignConfig, *, now: datetime) -> dict[str, Any]:
    return {
        "id": int(row.id or 0),
        "agent_id": int(row.agent_id or 0),
        "is_enabled": bool(row.is_enabled),
        "starts_at": row.starts_at.strftime("%Y-%m-%d %H:%M:%S") if row.starts_at else None,
        "ends_at": row.ends_at.strftime("%Y-%m-%d %H:%M:%S") if row.ends_at else None,
        "first_deposit_bonus_rate": float(row.first_deposit_bonus_rate or 0),
        "first_deposit_bonus_amount": float(row.first_deposit_bonus_amount or 0),
        "display_title": row.display_title,
        "display_subtitle": row.display_subtitle,
        "summary": _campaign_summary_text(row),
        "status": campaign_status_text(row, now=now),
    }


def upsert_agent_campaign_config(
    *,
    agent_id: int,
    actor_username: str,
    is_enabled: bool,
    starts_at: Any = None,
    ends_at: Any = None,
    first_deposit_bonus_rate: Any = Decimal("0"),
    first_deposit_bonus_amount: Any = Decimal("0"),
    display_title: Optional[str] = None,
    display_subtitle: Optional[str] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    starts_at_value = _parse_datetime(starts_at)
    ends_at_value = _parse_datetime(ends_at)
    if starts_at_value and ends_at_value and ends_at_value < starts_at_value:
        raise ValueError("Campaign end time must be greater than or equal to start time.")

    rate_value = _parse_decimal(first_deposit_bonus_rate, default="0")
    fixed_value = _parse_decimal(first_deposit_bonus_amount, default="0")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        agent = session.exec(select(Agent).where(Agent.id == int(agent_id))).first()
        if agent is None:
            raise ValueError("Agent not found.")

        actor = session.exec(
            select(AdminUser).where(AdminUser.username == str(actor_username or "").strip())
        ).first()

        row = session.exec(
            select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(agent_id))
        ).first()
        if row is None:
            row = AgentCampaignConfig(agent_id=int(agent_id))

        row.is_enabled = bool(is_enabled)
        row.starts_at = starts_at_value
        row.ends_at = ends_at_value
        row.first_deposit_bonus_rate = rate_value
        row.first_deposit_bonus_amount = fixed_value
        row.display_title = str(display_title or "").strip() or None
        row.display_subtitle = str(display_subtitle or "").strip() or None
        row.updated_by = int(actor.id or 0) if actor is not None else None
        row.updated_at = _now()

        session.add(row)
        session.commit()
        session.refresh(row)

        payload = _row_to_payload(row, now=_now())
        # Upsert response is interpreted as current admin-state confirmation.
        payload["status"] = "active" if bool(row.is_enabled) else "disabled"
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_agent_campaign_summary(
    *,
    agent_id: int,
    session: Session,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    row = session.exec(
        select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(agent_id))
    ).first()
    if row is None:
        return {
            "agent_id": int(agent_id),
            "is_enabled": False,
            "status": "disabled",
            "summary": "",
            "display_title": None,
            "display_subtitle": None,
            "starts_at": None,
            "ends_at": None,
            "first_deposit_bonus_rate": 0.0,
            "first_deposit_bonus_amount": 0.0,
        }
    return _row_to_payload(row, now=now or _now())


def get_active_campaign_for_bot(
    *,
    bot_id: int,
    now: Optional[datetime] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
        if bot is None or bot.owner_agent_id is None:
            return {}

        row = session.exec(
            select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(bot.owner_agent_id))
        ).first()
        if row is None:
            return {}

        current_time = now or _now()
        if campaign_status_text(row, now=current_time) != "active":
            return {}
        return _row_to_payload(row, now=current_time)
    finally:
        session.close()
