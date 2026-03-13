"""DB services for agent management page."""

from __future__ import annotations

import secrets
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus


def _generate_secure_temp_password() -> str:
    return f"Agent-{secrets.token_urlsafe(12)}-A1!"


def _mask_token(token: str) -> str:
    value = str(token or "").strip()
    if len(value) <= 14:
        return "****"
    return f"{value[:10]}...{value[-4:]}"


def _format_rate(rate: float) -> str:
    return f"{float(rate) * 100:.2f}%"


def _admin_username_base(name: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(name or "").lower()).strip("_")
    return text or "agent"


def _ensure_unique_admin_identity(session: Session, base: str) -> tuple[str, str]:
    username = base
    email = f"{username}@local.test"
    i = 1
    while session.exec(select(AdminUser).where(AdminUser.username == username)).first() is not None:
        i += 1
        username = f"{base}_{i}"
        email = f"{username}@local.test"
    return username, email


def _to_row(agent: Agent, bots: list[BotInstance]) -> dict[str, Any]:
    bot_rows = [item for item in bots if int(item.owner_agent_id or 0) == int(agent.id or 0)]
    primary_bot = bot_rows[0] if bot_rows else None
    total_users = sum(int(item.total_users or 0) for item in bot_rows)
    total_orders = sum(int(item.total_orders or 0) for item in bot_rows)
    return {
        "id": int(agent.id or 0),
        "name": str(agent.name),
        "contact_telegram": str(agent.contact_telegram or ""),
        "contact_email": str(agent.contact_email or ""),
        "bot_name": str(primary_bot.name if primary_bot else "未分配"),
        "bot_token": str(primary_bot.token if primary_bot else ""),
        "masked_token": _mask_token(str(primary_bot.token if primary_bot else "")) if primary_bot else "-",
        "profit_rate": float(agent.profit_rate or 0),
        "profit_rate_label": _format_rate(float(agent.profit_rate or 0)),
        "usdt_address": str(agent.usdt_address or ""),
        "is_active": bool(agent.is_active),
        "is_verified": bool(agent.is_verified),
        "total_bots": len(bot_rows),
        "total_users": total_users,
        "total_orders": total_orders,
        "total_profit": float(agent.total_profit or 0),
        "created_at": agent.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def list_agents_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        agents = list(session.exec(select(Agent).order_by(Agent.created_at.desc())).all())
        bots = list(session.exec(select(BotInstance).order_by(BotInstance.created_at.asc())).all())
        return [_to_row(item, bots) for item in agents]
    finally:
        session.close()


def get_agent_snapshot(
    *,
    agent_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    rows = list_agents_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(agent_id):
            return row
    raise ValueError("Agent not found.")


def create_agent_with_bot(
    *,
    name: str,
    contact_telegram: str,
    contact_email: str,
    bot_name: str,
    bot_token: str,
    profit_rate: float,
    usdt_address: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    bot_token_text = str(bot_token or "").strip()
    if not name_text:
        raise ValueError("Agent name is required.")
    if not bot_token_text:
        raise ValueError("Bot token is required.")
    rate = float(profit_rate)
    if rate < 0 or rate > 1:
        raise ValueError("Profit rate must be between 0 and 1.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        if session.exec(select(BotInstance).where(BotInstance.token == bot_token_text)).first() is not None:
            raise ValueError("Bot token already exists.")

        base = _admin_username_base(name_text)
        username, email = _ensure_unique_admin_identity(session, base)
        admin = AdminUser(
            username=username,
            email=email,
            password_hash="",
            role=AdminRole.AGENT,
            display_name=name_text,
            is_active=True,
            is_verified=True,
        )
        admin.set_password(_generate_secure_temp_password())
        session.add(admin)
        session.commit()
        session.refresh(admin)

        agent = Agent(
            admin_user_id=int(admin.id or 0),
            name=name_text,
            contact_telegram=str(contact_telegram or "").strip() or None,
            contact_email=str(contact_email or "").strip() or None,
            profit_rate=rate,
            usdt_address=str(usdt_address or "").strip() or None,
            is_active=True,
            is_verified=False,
            total_bots=1,
            total_users=0,
            total_orders=0,
            total_profit=0,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        bot = BotInstance(
            token=bot_token_text,
            name=str(bot_name or "").strip() or f"{name_text} Bot",
            username=re.sub(r"[^a-zA-Z0-9_]+", "_", name_text.lower()).strip("_") or None,
            owner_agent_id=int(agent.id or 0),
            is_platform_bot=False,
            usdt_address=str(usdt_address or "").strip() or None,
            status=BotStatus.ACTIVE,
            is_enabled=True,
            total_users=0,
            total_orders=0,
            total_revenue=0,
        )
        session.add(bot)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_agents_snapshot(session_factory=session_factory)
    for row in rows:
        if row["name"] == name_text:
            return row
    raise ValueError("Created agent not found in snapshot.")


def update_agent_record(
    *,
    agent_id: int,
    name: str,
    contact_telegram: str,
    contact_email: str,
    bot_name: str,
    bot_token: str,
    profit_rate: float,
    usdt_address: str,
    is_verified: bool,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    token_text = str(bot_token or "").strip()
    if not name_text:
        raise ValueError("Agent name is required.")
    if not token_text:
        raise ValueError("Bot token is required.")

    rate = float(profit_rate)
    if rate < 0 or rate > 1:
        raise ValueError("Profit rate must be between 0 and 1.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        agent = session.exec(select(Agent).where(Agent.id == int(agent_id))).first()
        if agent is None:
            raise ValueError("Agent not found.")

        duplicate_bot = session.exec(
            select(BotInstance).where(BotInstance.token == token_text)
        ).first()
        if duplicate_bot is not None and int(duplicate_bot.owner_agent_id or 0) != int(agent_id):
            raise ValueError("Bot token already exists.")

        agent.name = name_text
        agent.contact_telegram = str(contact_telegram or "").strip() or None
        agent.contact_email = str(contact_email or "").strip() or None
        agent.profit_rate = rate
        agent.usdt_address = str(usdt_address or "").strip() or None
        agent.is_verified = bool(is_verified)
        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(agent)

        bot = session.exec(
            select(BotInstance)
            .where(BotInstance.owner_agent_id == int(agent_id))
            .order_by(BotInstance.id.asc())
        ).first()
        if bot is None:
            bot = BotInstance(
                token=token_text,
                name=str(bot_name or "").strip() or f"{name_text} Bot",
                owner_agent_id=int(agent_id),
                is_platform_bot=False,
                status=BotStatus.ACTIVE,
                is_enabled=True,
            )
        else:
            bot.token = token_text
            bot.name = str(bot_name or "").strip() or f"{name_text} Bot"
            bot.usdt_address = str(usdt_address or "").strip() or None
            bot.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(bot)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_agents_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(agent_id):
            return row
    raise ValueError("Updated agent not found in snapshot.")


def toggle_agent_record_status(
    *,
    agent_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        agent = session.exec(select(Agent).where(Agent.id == int(agent_id))).first()
        if agent is None:
            raise ValueError("Agent not found.")
        agent.is_active = not bool(agent.is_active)
        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(agent)

        bots = list(session.exec(select(BotInstance).where(BotInstance.owner_agent_id == int(agent_id))).all())
        for bot in bots:
            if agent.is_active:
                bot.is_enabled = True
                bot.status = BotStatus.ACTIVE
            else:
                bot.is_enabled = False
                bot.status = BotStatus.INACTIVE
            bot.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.add(bot)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_agents_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(agent_id):
            return row
    raise ValueError("Toggled agent not found in snapshot.")
