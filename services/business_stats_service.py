from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlmodel import Session, select

from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance
from shared.models.bot_user_account import BotUserAccount
from shared.models.order import Order, OrderStatus
from shared.models.user import User
from shared.models.user_export import UserBotSource


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _status_text(value: object) -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value or "")


def _revenue_statuses() -> set[str]:
    return {OrderStatus.PAID.value, OrderStatus.COMPLETED.value}


def _bot_user_ids(session: Session, *, bot_id: int) -> set[int]:
    bot_value = int(bot_id or 0)
    if bot_value <= 0:
        return set()

    user_ids: set[int] = set()
    for row in session.exec(select(User.id).where(User.from_bot_id == bot_value)).all():
        user_ids.add(int(row))
    for row in session.exec(select(UserBotSource.user_id).where(UserBotSource.bot_id == bot_value)).all():
        user_ids.add(int(row))
    for row in session.exec(select(BotUserAccount.user_id).where(BotUserAccount.bot_id == bot_value)).all():
        user_ids.add(int(row))
    return user_ids


def get_bot_business_truth(session: Session, *, bot_id: int) -> dict[str, object]:
    bot_value = int(bot_id or 0)
    user_ids = _bot_user_ids(session, bot_id=bot_value)
    orders = list(session.exec(select(Order).where(Order.bot_id == bot_value)).all())
    total_revenue = _money(
        sum(
            float(row.total_amount or 0)
            for row in orders
            if _status_text(row.status) in _revenue_statuses()
        )
    )
    return {
        "bot_id": bot_value,
        "total_users": len(user_ids),
        "total_orders": len(orders),
        "total_revenue": total_revenue,
    }


def sync_bot_business_fields(session: Session, *, bot_id: int) -> None:
    bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
    if bot is None:
        return
    truth = get_bot_business_truth(session, bot_id=int(bot.id or 0))
    bot.total_users = int(truth["total_users"])
    bot.total_orders = int(truth["total_orders"])
    bot.total_revenue = _money(truth["total_revenue"])
    bot.updated_at = _now()
    session.add(bot)


def _owned_bot_ids(session: Session, *, agent_id: int) -> list[int]:
    return [
        int(row.id or 0)
        for row in session.exec(
            select(BotInstance).where(BotInstance.owner_agent_id == int(agent_id))
        ).all()
        if int(row.id or 0) > 0
    ]


def get_agent_business_truth(session: Session, *, agent_id: int) -> dict[str, object]:
    agent = session.exec(select(Agent).where(Agent.id == int(agent_id))).first()
    if agent is None:
        raise ValueError("Agent not found.")

    bot_ids = _owned_bot_ids(session, agent_id=int(agent.id or 0))
    user_ids: set[int] = set()
    for bot_id in bot_ids:
        user_ids.update(_bot_user_ids(session, bot_id=bot_id))

    orders = list(
        session.exec(select(Order).where(Order.bot_id.in_(list(bot_ids)))).all()  # type: ignore[arg-type]
    ) if bot_ids else []

    truth_profit = _money(
        sum(
            float(row.agent_profit or 0)
            for row in orders
            if _status_text(row.status) in _revenue_statuses()
        )
    )
    return {
        "agent_id": int(agent.id or 0),
        "total_bots": len(bot_ids),
        "total_users": len(user_ids),
        "total_orders": len(orders),
        "total_profit": truth_profit,
        "frozen_balance": truth_profit,
        # Balance stays the explicit withdrawable bucket until a separate release flow exists.
        "balance": _money(agent.balance or 0),
    }


def sync_agent_business_fields(session: Session, *, agent_id: int) -> None:
    agent = session.exec(select(Agent).where(Agent.id == int(agent_id))).first()
    if agent is None:
        return
    truth = get_agent_business_truth(session, agent_id=int(agent.id or 0))
    agent.total_bots = int(truth["total_bots"])
    agent.total_users = int(truth["total_users"])
    agent.total_orders = int(truth["total_orders"])
    agent.total_profit = _money(truth["total_profit"])
    agent.frozen_balance = _money(truth["frozen_balance"])
    agent.balance = _money(truth["balance"])
    agent.updated_at = _now()
    session.add(agent)


def sync_bot_and_related_agent_fields(
    session: Session,
    *,
    bot_id: int,
    extra_agent_ids: Iterable[int] | None = None,
) -> None:
    sync_bot_business_fields(session, bot_id=int(bot_id))
    bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
    agent_ids = {int(item) for item in extra_agent_ids or [] if int(item or 0) > 0}
    if bot is not None and int(bot.owner_agent_id or 0) > 0:
        agent_ids.add(int(bot.owner_agent_id or 0))
    for agent_id in sorted(agent_ids):
        sync_agent_business_fields(session, agent_id=agent_id)
