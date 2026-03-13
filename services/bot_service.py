"""DB services for bot management page."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.agent import Agent
from shared.models.balance_ledger import BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.cart import CartItem
from shared.models.deposit import Deposit
from shared.models.order import Order, OrderStatus
from shared.models.product import ProductItem
from shared.models.user import User
from shared.models.user_export import UserBotSource
from shared.models.wallet import WalletAddress


def _mask_token(token: str) -> str:
    value = str(token or "").strip()
    if len(value) <= 14:
        return "****"
    return f"{value[:10]}...{value[-4:]}"


def _status_text(status: Any) -> str:
    if hasattr(status, "value"):
        return str(status.value)
    return str(status or "")


def _is_active_enabled(bot: BotInstance) -> bool:
    return bool(bot.is_enabled) and _status_text(bot.status) == BotStatus.ACTIVE.value


def _pick_runtime_bot_id(bots: list[BotInstance]) -> Optional[int]:
    # Backward-compatible single pick helper. Multi-bot runtime uses list_runtime_bot_bindings.
    for bot in bots:
        if bool(bot.is_platform_bot) and _is_active_enabled(bot):
            return int(bot.id or 0)
    for bot in bots:
        if _is_active_enabled(bot):
            return int(bot.id or 0)
    return None


def _owner_name(bot: BotInstance, agent_map: dict[int, Agent]) -> str:
    if bot.is_platform_bot or not bot.owner_agent_id:
        return "平台自营"
    agent = agent_map.get(int(bot.owner_agent_id))
    return str(agent.name if agent else "平台自营")


def _to_row(
    bot: BotInstance,
    agent_map: dict[int, Agent],
    *,
    user_count_map: dict[int, int],
    order_count_map: dict[int, int],
    revenue_map: dict[int, float],
) -> dict[str, Any]:
    bot_id = int(bot.id or 0)
    return {
        "id": bot_id,
        "name": str(bot.name),
        "username": str(bot.username or ""),
        "token_masked": _mask_token(str(bot.token or "")),
        "status": _status_text(bot.status),
        "is_enabled": bool(bot.is_enabled),
        "is_platform_bot": bool(bot.is_platform_bot),
        "runtime_selected": _is_active_enabled(bot),
        "owner": _owner_name(bot, agent_map),
        "usdt_address": str(bot.usdt_address or ""),
        "users": int(user_count_map.get(bot_id, int(bot.total_users or 0))),
        "orders": int(order_count_map.get(bot_id, int(bot.total_orders or 0))),
        "revenue": float(revenue_map.get(bot_id, float(bot.total_revenue or 0))),
        "created_at": bot.created_at.strftime("%Y-%m-%d"),
    }


def _aggregate_bot_metrics(
    session: Session,
    *,
    bot_ids: set[int],
) -> tuple[dict[int, int], dict[int, int], dict[int, float]]:
    user_count_map: dict[int, int] = {}
    order_count_map: dict[int, int] = {}
    revenue_map: dict[int, float] = {}

    if bot_ids:
        accounts = list(
            session.exec(select(BotUserAccount).where(BotUserAccount.bot_id.in_(list(bot_ids)))).all()  # type: ignore[arg-type]
        )
        for row in accounts:
            bid = int(row.bot_id)
            user_count_map[bid] = user_count_map.get(bid, 0) + 1

        orders = list(
            session.exec(select(Order).where(Order.bot_id.in_(list(bot_ids)))).all()  # type: ignore[arg-type]
        )
        for row in orders:
            bid = int(row.bot_id)
            order_count_map[bid] = order_count_map.get(bid, 0) + 1
            status_text = _status_text(row.status)
            if status_text in {OrderStatus.PAID.value, OrderStatus.COMPLETED.value}:
                revenue_map[bid] = round(revenue_map.get(bid, 0.0) + float(row.total_amount or 0), 2)
    return user_count_map, order_count_map, revenue_map


def list_bot_owner_options(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[str]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        agents = list(session.exec(select(Agent).order_by(Agent.id.asc())).all())
        options = ["平台自营"]
        options.extend([str(item.name) for item in agents if str(item.name).strip()])
        return options
    finally:
        session.close()


def list_bots_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bots = list(session.exec(select(BotInstance).order_by(BotInstance.created_at.desc())).all())
        bot_ids = {int(item.id or 0) for item in bots if int(item.id or 0) > 0}
        agent_ids = {int(item.owner_agent_id or 0) for item in bots if item.owner_agent_id}
        agents = list(session.exec(select(Agent)).all())
        agent_map = {
            int(item.id or 0): item
            for item in agents
            if int(item.id or 0) in agent_ids
        }
        user_count_map, order_count_map, revenue_map = _aggregate_bot_metrics(session, bot_ids=bot_ids)
        return [
            _to_row(
                item,
                agent_map,
                user_count_map=user_count_map,
                order_count_map=order_count_map,
                revenue_map=revenue_map,
            )
            for item in bots
        ]
    finally:
        session.close()


def list_runtime_bot_bindings(
    *,
    preferred_token: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bots = list(session.exec(select(BotInstance).order_by(BotInstance.id.asc())).all())
        payload: list[dict[str, Any]] = []
        for bot in bots:
            if not _is_active_enabled(bot):
                continue
            payload.append(
                {
                    "id": int(bot.id or 0),
                    "name": str(bot.name or "Runtime Bot"),
                    "username": str(bot.username or ""),
                    "token": str(bot.token or ""),
                    "source": "database",
                    "masked_token": _mask_token(str(bot.token or "")),
                }
            )
        if payload:
            return payload

        token_text = str(preferred_token or "").strip()
        if token_text:
            return [
                {
                    "id": None,
                    "name": "Env Bot",
                    "username": "",
                    "token": token_text,
                    "source": "env",
                    "masked_token": "****",
                }
            ]
        return []
    finally:
        session.close()


def resolve_runtime_bot_binding(
    *,
    preferred_token: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bots = list(session.exec(select(BotInstance).order_by(BotInstance.created_at.asc())).all())
        if not bots:
            raise ValueError("No bot instance available.")

        token_text = str(preferred_token or "").strip()
        selected: Optional[BotInstance] = None
        source = "database"
        if token_text:
            selected = next((item for item in bots if str(item.token) == token_text), None)
            if selected is not None:
                source = "preferred_token"

        if selected is None:
            runtime_bot_id = _pick_runtime_bot_id(bots)
            if runtime_bot_id is None:
                raise ValueError("No active bot instance available.")
            selected = next((item for item in bots if int(item.id or 0) == int(runtime_bot_id)), None)

        if selected is None:
            raise ValueError("Runtime bot not found.")

        return {
            "id": int(selected.id or 0),
            "name": str(selected.name or "Runtime Bot"),
            "username": str(selected.username or ""),
            "token": str(selected.token or ""),
            "source": source,
            "masked_token": _mask_token(str(selected.token or "")),
        }
    finally:
        session.close()


def get_bot_snapshot(
    *,
    bot_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    rows = list_bots_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(bot_id):
            return row
    raise ValueError("Bot not found.")


def _resolve_owner_name(session: Session, owner_name: str) -> tuple[Optional[int], bool]:
    owner = str(owner_name or "").strip()
    if not owner or owner == "平台自营":
        return None, True
    row = session.exec(select(Agent).where(Agent.name == owner)).first()
    if row is None:
        raise ValueError("Owner agent not found.")
    return int(row.id or 0), False


def create_bot_record(
    *,
    name: str,
    token: str,
    owner_name: str,
    usdt_address: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    token_text = str(token or "").strip()
    if not name_text:
        raise ValueError("Bot name is required.")
    if not token_text:
        raise ValueError("Bot token is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        exists = session.exec(select(BotInstance).where(BotInstance.token == token_text)).first()
        if exists is not None:
            raise ValueError("Bot token already exists.")

        owner_agent_id, is_platform_bot = _resolve_owner_name(session, owner_name)
        username = re.sub(r"[^a-zA-Z0-9_]+", "_", name_text.lower()).strip("_")

        bot = BotInstance(
            token=token_text,
            name=name_text,
            username=username or None,
            owner_agent_id=owner_agent_id,
            is_platform_bot=is_platform_bot,
            usdt_address=str(usdt_address or "").strip() or None,
            status=BotStatus.INACTIVE,
            is_enabled=False,
            total_users=0,
            total_orders=0,
            total_revenue=0,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_bots_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(bot.id or 0):
            return row
    raise ValueError("Created bot not found in snapshot.")


def update_bot_record(
    *,
    bot_id: int,
    name: str,
    owner_name: str,
    usdt_address: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    if not name_text:
        raise ValueError("Bot name is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
        if bot is None:
            raise ValueError("Bot not found.")

        owner_agent_id, is_platform_bot = _resolve_owner_name(session, owner_name)
        bot.name = name_text
        bot.owner_agent_id = owner_agent_id
        bot.is_platform_bot = is_platform_bot
        bot.usdt_address = str(usdt_address or "").strip() or None
        bot.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(bot)
        session.commit()
        session.refresh(bot)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_bots_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(bot_id):
            return row
    raise ValueError("Updated bot not found in snapshot.")


def _pick_fallback_bot_id(session: Session, *, exclude_bot_id: int) -> Optional[int]:
    rows = list(
        session.exec(
            select(BotInstance)
            .where(BotInstance.id != int(exclude_bot_id))
            .order_by(BotInstance.id.asc())
        ).all()
    )
    if not rows:
        return None
    for row in rows:
        if bool(row.is_platform_bot) and _is_active_enabled(row):
            return int(row.id or 0)
    for row in rows:
        if _is_active_enabled(row):
            return int(row.id or 0)
    return int(rows[0].id or 0)


def delete_bot_record(
    *,
    bot_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> None:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        target_bot_id = int(bot_id)
        bot = session.exec(select(BotInstance).where(BotInstance.id == target_bot_id)).first()
        if bot is None:
            raise ValueError("Bot not found.")

        fallback_bot_id = _pick_fallback_bot_id(session, exclude_bot_id=target_bot_id)

        orders = list(session.exec(select(Order).where(Order.bot_id == target_bot_id)).all())
        deposits = list(session.exec(select(Deposit).where(Deposit.bot_id == target_bot_id)).all())
        user_sources = list(session.exec(select(UserBotSource).where(UserBotSource.bot_id == target_bot_id)).all())
        accounts = list(session.exec(select(BotUserAccount).where(BotUserAccount.bot_id == target_bot_id)).all())
        has_required_refs = bool(orders or deposits or user_sources or accounts)
        if has_required_refs and fallback_bot_id is None:
            raise ValueError("该 Bot 存在关联订单/充值/用户来源，无法删除。请先保留至少一个 Bot 后重试。")

        for row in orders:
            row.bot_id = int(fallback_bot_id or 0)
            session.add(row)
        for row in deposits:
            row.bot_id = int(fallback_bot_id or 0)
            session.add(row)

        for row in user_sources:
            existing = session.exec(
                select(UserBotSource)
                .where(UserBotSource.user_id == int(row.user_id))
                .where(UserBotSource.bot_id == int(fallback_bot_id or 0))
            ).first() if fallback_bot_id is not None else None
            if existing is not None:
                if bool(row.is_primary) and not bool(existing.is_primary):
                    existing.is_primary = True
                    session.add(existing)
                session.delete(row)
                continue
            row.bot_id = int(fallback_bot_id or 0)
            session.add(row)

        for row in accounts:
            existing = (
                session.exec(
                    select(BotUserAccount)
                    .where(BotUserAccount.user_id == int(row.user_id))
                    .where(BotUserAccount.bot_id == int(fallback_bot_id or 0))
                ).first()
                if fallback_bot_id is not None
                else None
            )
            if existing is not None:
                existing.balance = Decimal(str(existing.balance or 0)) + Decimal(str(row.balance or 0))
                existing.total_deposit = Decimal(str(existing.total_deposit or 0)) + Decimal(str(row.total_deposit or 0))
                existing.total_spent = Decimal(str(existing.total_spent or 0)) + Decimal(str(row.total_spent or 0))
                existing.order_count = int(existing.order_count or 0) + int(row.order_count or 0)
                existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.add(existing)
                session.delete(row)
                continue
            row.bot_id = int(fallback_bot_id or 0)
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.add(row)

        users = list(session.exec(select(User).where(User.from_bot_id == target_bot_id)).all())
        for row in users:
            row.from_bot_id = int(fallback_bot_id) if fallback_bot_id is not None else None
            session.add(row)

        wallets = list(session.exec(select(WalletAddress).where(WalletAddress.bot_id == target_bot_id)).all())
        for row in wallets:
            row.bot_id = int(fallback_bot_id) if fallback_bot_id is not None else None
            session.add(row)

        carts = list(session.exec(select(CartItem).where(CartItem.bot_id == target_bot_id)).all())
        for row in carts:
            row.bot_id = int(fallback_bot_id) if fallback_bot_id is not None else None
            session.add(row)

        ledgers = list(session.exec(select(BalanceLedger).where(BalanceLedger.bot_id == target_bot_id)).all())
        for row in ledgers:
            row.bot_id = int(fallback_bot_id) if fallback_bot_id is not None else None
            session.add(row)

        products = list(session.exec(select(ProductItem).where(ProductItem.sold_to_bot_id == target_bot_id)).all())
        for row in products:
            row.sold_to_bot_id = int(fallback_bot_id) if fallback_bot_id is not None else None
            session.add(row)

        session.delete(bot)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def toggle_bot_record_status(
    *,
    bot_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
        if bot is None:
            raise ValueError("Bot not found.")

        current = _status_text(bot.status)
        if current == BotStatus.ACTIVE.value:
            bot.status = BotStatus.INACTIVE
            bot.is_enabled = False
        else:
            bot.status = BotStatus.ACTIVE
            bot.is_enabled = True
        bot.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(bot)
        session.commit()
        session.refresh(bot)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_bots_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(bot_id):
            return row
    raise ValueError("Toggled bot not found in snapshot.")
