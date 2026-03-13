"""Database-backed user page services."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit
from shared.models.order import Order, OrderItem
from shared.models.user import User
from shared.models.user_export import UserBotSource


UserSnapshot = dict[str, Any]

_ACTION_TO_LABEL = {
    BalanceAction.CREDIT.value: "充值",
    BalanceAction.DEBIT.value: "扣款",
    BalanceAction.REFUND.value: "退款",
    BalanceAction.MANUAL.value: "手动",
}


def _dt_text(value: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    return value.strftime(fmt)


def _normalize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _username_text(username: Optional[str]) -> Optional[str]:
    if username is None:
        return None
    text = str(username).strip()
    if not text:
        return None
    if text.startswith("@"):
        return text
    return f"@{text}"


def _resolve_bot(
    *,
    user: User,
    source_bot_name: str,
    bot_map: dict[int, BotInstance],
    session: Session,
) -> Optional[BotInstance]:
    name = str(source_bot_name or "").strip()
    if name:
        if name.isdigit():
            numeric_id = int(name)
            if numeric_id in bot_map:
                return bot_map[numeric_id]
            row = session.exec(select(BotInstance).where(BotInstance.id == numeric_id)).first()
            if row is not None:
                return row
        for bot in bot_map.values():
            if bot.name == name:
                return bot
        row = session.exec(select(BotInstance).where(BotInstance.name == name)).first()
        if row is not None:
            return row

    if user.from_bot_id and int(user.from_bot_id) in bot_map:
        return bot_map[int(user.from_bot_id)]
    if user.from_bot_id:
        row = session.exec(select(BotInstance).where(BotInstance.id == int(user.from_bot_id))).first()
        if row is not None:
            return row

    return session.exec(select(BotInstance).order_by(BotInstance.id.asc())).first()


def _ensure_bot_account(session: Session, *, user: User, bot: BotInstance) -> BotUserAccount:
    account = session.exec(
        select(BotUserAccount)
        .where(BotUserAccount.user_id == int(user.id or 0))
        .where(BotUserAccount.bot_id == int(bot.id or 0))
    ).first()
    if account is not None:
        return account

    has_any = session.exec(select(BotUserAccount.id).where(BotUserAccount.user_id == int(user.id or 0))).first()
    seed_balance = _normalize_amount(user.balance or 0) if has_any is None else Decimal("0.00")
    seed_total_deposit = _normalize_amount(user.total_deposit or 0) if has_any is None else Decimal("0.00")
    seed_total_spent = _normalize_amount(user.total_spent or 0) if has_any is None else Decimal("0.00")

    account = BotUserAccount(
        user_id=int(user.id or 0),
        bot_id=int(bot.id or 0),
        balance=seed_balance,
        total_deposit=seed_total_deposit,
        total_spent=seed_total_spent,
        order_count=0,
        is_banned=False,
        ban_reason=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        last_active_at=user.last_active_at,
    )
    session.add(account)
    session.flush()
    return account


def _sync_user_aggregate_from_accounts(session: Session, *, user: User) -> None:
    rows = list(session.exec(select(BotUserAccount).where(BotUserAccount.user_id == int(user.id or 0))).all())
    if not rows:
        return
    user.balance = _normalize_amount(sum(float(item.balance or 0) for item in rows))
    user.total_deposit = _normalize_amount(sum(float(item.total_deposit or 0) for item in rows))
    user.total_spent = _normalize_amount(sum(float(item.total_spent or 0) for item in rows))
    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(user)


def _ordered_bot_ids(
    *,
    source_rows_for_user: list[UserBotSource],
    account_by_bot: dict[int, BotUserAccount],
    deposits_for_user: list[Deposit],
    ledgers_for_user: list[BalanceLedger],
    orders_for_user: list[Order],
    user: User,
) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()

    def _add(bot_id: int) -> None:
        value = int(bot_id or 0)
        if value <= 0 or value in seen:
            return
        seen.add(value)
        ordered.append(value)

    for row in source_rows_for_user:
        _add(int(row.bot_id))
    for bot_id in sorted(account_by_bot.keys()):
        _add(bot_id)
    for row in deposits_for_user:
        _add(int(row.bot_id))
    for row in ledgers_for_user:
        if row.bot_id:
            _add(int(row.bot_id))
    for row in orders_for_user:
        _add(int(row.bot_id))
    if user.from_bot_id:
        _add(int(user.from_bot_id))
    return ordered


def list_users_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[UserSnapshot]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        users = list(session.exec(select(User).order_by(User.created_at.desc())).all())
        if not users:
            return []

        user_ids = {int(user.id or 0) for user in users}
        source_rows = list(session.exec(select(UserBotSource)).all())
        deposits = list(session.exec(select(Deposit).order_by(Deposit.created_at.desc())).all())
        ledgers = list(session.exec(select(BalanceLedger).order_by(BalanceLedger.created_at.desc())).all())
        orders = list(session.exec(select(Order).order_by(Order.created_at.desc())).all())
        order_items = list(session.exec(select(OrderItem)).all())
        accounts = list(session.exec(select(BotUserAccount)).all())

        source_map: dict[int, list[UserBotSource]] = {}
        deposit_map: dict[int, list[Deposit]] = {}
        ledger_map: dict[int, list[BalanceLedger]] = {}
        order_map: dict[int, list[Order]] = {}
        account_map: dict[int, dict[int, BotUserAccount]] = {}
        order_ids: set[int] = set()
        bot_ids: set[int] = set()
        order_count_by_user_bot: dict[tuple[int, int], int] = {}

        for row in source_rows:
            uid = int(row.user_id)
            if uid not in user_ids:
                continue
            source_map.setdefault(uid, []).append(row)
            bot_ids.add(int(row.bot_id))

        for row in deposits:
            uid = int(row.user_id)
            if uid not in user_ids:
                continue
            deposit_map.setdefault(uid, []).append(row)
            bot_ids.add(int(row.bot_id))

        for row in ledgers:
            uid = int(row.user_id)
            if uid not in user_ids:
                continue
            ledger_map.setdefault(uid, []).append(row)
            if row.bot_id:
                bot_ids.add(int(row.bot_id))

        for row in orders:
            uid = int(row.user_id)
            if uid not in user_ids:
                continue
            order_map.setdefault(uid, []).append(row)
            order_ids.add(int(row.id or 0))
            bot_ids.add(int(row.bot_id))
            key = (uid, int(row.bot_id))
            order_count_by_user_bot[key] = order_count_by_user_bot.get(key, 0) + 1

        for row in accounts:
            uid = int(row.user_id)
            if uid not in user_ids:
                continue
            bid = int(row.bot_id)
            account_map.setdefault(uid, {})[bid] = row
            bot_ids.add(bid)

        item_map: dict[int, list[OrderItem]] = {}
        for row in order_items:
            oid = int(row.order_id)
            if oid not in order_ids:
                continue
            item_map.setdefault(oid, []).append(row)

        for user in users:
            if user.from_bot_id:
                bot_ids.add(int(user.from_bot_id))

        bots = list(session.exec(select(BotInstance)).all())
        bot_map = {int(bot.id or 0): bot for bot in bots if int(bot.id or 0) in bot_ids}

        snapshots: list[UserSnapshot] = []
        for user in users:
            uid = int(user.id or 0)
            source_rows_for_user = sorted(
                source_map.get(uid, []),
                key=lambda item: (not bool(item.is_primary), int(item.id or 0)),
            )
            account_by_bot = account_map.get(uid, {})
            ordered_bot_ids = _ordered_bot_ids(
                source_rows_for_user=source_rows_for_user,
                account_by_bot=account_by_bot,
                deposits_for_user=deposit_map.get(uid, []),
                ledgers_for_user=ledger_map.get(uid, []),
                orders_for_user=order_map.get(uid, []),
                user=user,
            )

            primary_bot_id = 0
            for row in source_rows_for_user:
                if bool(row.is_primary):
                    primary_bot_id = int(row.bot_id)
                    break
            if primary_bot_id <= 0 and user.from_bot_id:
                primary_bot_id = int(user.from_bot_id)
            if primary_bot_id <= 0 and ordered_bot_ids:
                primary_bot_id = int(ordered_bot_ids[0])

            bot_sources: list[dict[str, Any]] = []
            for bid in ordered_bot_ids:
                bot = bot_map.get(int(bid))
                account = account_by_bot.get(int(bid))
                source_status = "banned" if bool(user.is_banned) or bool(account.is_banned if account else False) else "active"
                bot_sources.append(
                    {
                        "bot_id": int(bid),
                        "bot_name": str(bot.name if bot else f"Bot-{bid}"),
                        "balance": round(float(account.balance or 0), 2) if account else 0.0,
                        "total_deposit": round(float(account.total_deposit or 0), 2) if account else 0.0,
                        "total_spent": round(float(account.total_spent or 0), 2) if account else 0.0,
                        "orders": int(order_count_by_user_bot.get((uid, int(bid)), 0)),
                        "status": source_status,
                        "is_banned": source_status == "banned",
                    }
                )

            primary_bot = "-"
            primary_bot_status = "active"
            if primary_bot_id > 0:
                primary = next((row for row in bot_sources if int(row["bot_id"]) == int(primary_bot_id)), None)
                if primary is not None:
                    primary_bot = str(primary["bot_name"])
                    primary_bot_status = str(primary["status"])

            if account_by_bot:
                total_balance = _normalize_amount(sum(float(item.balance or 0) for item in account_by_bot.values()))
                total_deposit = _normalize_amount(sum(float(item.total_deposit or 0) for item in account_by_bot.values()))
                total_spent = _normalize_amount(sum(float(item.total_spent or 0) for item in account_by_bot.values()))
            else:
                total_balance = _normalize_amount(user.balance or 0)
                total_deposit = _normalize_amount(user.total_deposit or 0)
                total_spent = _normalize_amount(user.total_spent or 0)

            deposit_records: list[dict[str, Any]] = []
            for dep in deposit_map.get(uid, []):
                dep_bot = bot_map.get(int(dep.bot_id))
                deposit_records.append(
                    {
                        "record_no": str(dep.deposit_no),
                        "action": "充值",
                        "amount": float(dep.amount),
                        "remark": str(dep.operator_remark or ""),
                        "bot_name": str(dep_bot.name if dep_bot else f"Bot-{dep.bot_id}"),
                        "created_at": _dt_text(dep.created_at),
                    }
                )

            for ledger in ledger_map.get(uid, []):
                action_value = str(ledger.action.value if hasattr(ledger.action, "value") else ledger.action)
                action_label = _ACTION_TO_LABEL.get(action_value, action_value)
                if action_label == "退款":
                    continue
                bot_name = "-"
                if ledger.bot_id:
                    bot = bot_map.get(int(ledger.bot_id))
                    bot_name = str(bot.name if bot else f"Bot-{ledger.bot_id}")
                deposit_records.append(
                    {
                        "record_no": str(ledger.request_id or f"LEDGER-{ledger.id}"),
                        "action": action_label,
                        "amount": float(ledger.amount),
                        "remark": str(ledger.remark or ""),
                        "bot_name": bot_name,
                        "created_at": _dt_text(ledger.created_at),
                    }
                )

            deposit_records = sorted(
                deposit_records,
                key=lambda item: str(item.get("created_at", "")),
                reverse=True,
            )

            purchase_records: list[dict[str, Any]] = []
            for order in order_map.get(uid, []):
                order_status = order.status.value if hasattr(order.status, "value") else str(order.status)
                order_bot = bot_map.get(int(order.bot_id))
                order_item_rows = item_map.get(int(order.id or 0), [])
                first_item_name = str(order_item_rows[0].category_name) if order_item_rows else str(order.order_no)
                purchase_records.append(
                    {
                        "order_no": str(order.order_no),
                        "item": first_item_name,
                        "amount": float(order.total_amount),
                        "status": order_status,
                        "bot_name": str(order_bot.name if order_bot else f"Bot-{order.bot_id}"),
                        "created_at": _dt_text(order.created_at),
                    }
                )

            snapshots.append(
                {
                    "id": uid,
                    "telegram_id": str(user.telegram_id),
                    "username": _username_text(user.username),
                    "name": user.display_name,
                    "balance": round(float(total_balance), 2),
                    "total_deposit": round(float(total_deposit), 2),
                    "total_spent": round(float(total_spent), 2),
                    "orders": len(order_map.get(uid, [])),
                    "status": "banned" if bool(user.is_banned) else "active",
                    "bot_sources": bot_sources,
                    "primary_bot": primary_bot,
                    "primary_bot_status": primary_bot_status,
                    "created_at": _dt_text(user.created_at, "%Y-%m-%d"),
                    "last_active": _dt_text(user.last_active_at or user.updated_at),
                    "deposit_records": deposit_records,
                    "purchase_records": purchase_records,
                }
            )

        return snapshots
    finally:
        session.close()


def get_user_snapshot(
    *,
    user_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> UserSnapshot:
    rows = list_users_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(user_id):
            return row
    raise ValueError("User not found.")


def list_user_deposit_records(
    *,
    user_id: int,
    source_bot_name: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    row = get_user_snapshot(user_id=user_id, session_factory=session_factory)
    records = row.get("deposit_records") or []
    payload = list(records) if isinstance(records, list) else []
    bot_name = str(source_bot_name or "").strip()
    if not bot_name or bot_name in {"全部 Bot", "all", "ALL"}:
        return payload
    return [item for item in payload if str(item.get("bot_name") or "") == bot_name]


def list_user_purchase_records(
    *,
    user_id: int,
    source_bot_name: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    row = get_user_snapshot(user_id=user_id, session_factory=session_factory)
    records = row.get("purchase_records") or []
    payload = list(records) if isinstance(records, list) else []
    bot_name = str(source_bot_name or "").strip()
    if not bot_name or bot_name in {"全部 Bot", "all", "ALL"}:
        return payload
    return [item for item in payload if str(item.get("bot_name") or "") == bot_name]


def toggle_user_ban(
    *,
    user_id: int,
    operator_username: str,
    scope: str = "global",
    source_bot_name: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = session.exec(select(User).where(User.id == int(user_id))).first()
        if user is None:
            raise ValueError("User not found.")

        operator = session.exec(
            select(AdminUser).where(AdminUser.username == str(operator_username or "").strip())
        ).first()

        scope_text = str(scope or "global").strip().lower()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if scope_text == "bot":
            bot_map = {int(item.id or 0): item for item in session.exec(select(BotInstance)).all()}
            bot = _resolve_bot(
                user=user,
                source_bot_name=source_bot_name,
                bot_map=bot_map,
                session=session,
            )
            if bot is None:
                raise ValueError("Bot not found.")

            account = _ensure_bot_account(session, user=user, bot=bot)
            account.is_banned = not bool(account.is_banned)
            account.updated_at = now
            session.add(account)

            bot_status = "banned" if bool(account.is_banned) else "active"
            session.add(
                AdminAuditLog(
                    operator_id=int(operator.id or 0) if operator else None,
                    action="users.toggle_ban.bot",
                    target_type="user",
                    target_id=int(user.id or 0),
                    request_id=f"users-toggle-ban-bot-{user.id}-{now:%Y%m%d%H%M%S%f}",
                    detail_json=json.dumps(
                        {
                            "scope": "bot",
                            "user_id": int(user.id or 0),
                            "bot_id": int(bot.id or 0),
                            "bot_name": str(bot.name or f"Bot-{bot.id}"),
                            "status": bot_status,
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            session.commit()
            return {
                "id": int(user.id or 0),
                "scope": "bot",
                "status": "banned" if bool(user.is_banned) else "active",
                "bot_id": int(bot.id or 0),
                "bot_name": str(bot.name or f"Bot-{bot.id}"),
                "bot_status": bot_status,
            }

        user.is_banned = not bool(user.is_banned)
        user.updated_at = now
        session.add(user)

        new_status = "banned" if user.is_banned else "active"
        session.add(
            AdminAuditLog(
                operator_id=int(operator.id or 0) if operator else None,
                action="users.toggle_ban.global",
                target_type="user",
                target_id=int(user.id or 0),
                request_id=f"users-toggle-ban-global-{user.id}-{now:%Y%m%d%H%M%S%f}",
                detail_json=json.dumps(
                    {
                        "scope": "global",
                        "user_id": int(user.id or 0),
                        "status": new_status,
                    },
                    ensure_ascii=False,
                ),
            )
        )

        session.commit()
        session.refresh(user)
        return {"id": int(user.id or 0), "scope": "global", "status": new_status}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def adjust_user_balance(
    *,
    user_id: int,
    action: str,
    amount: Decimal,
    remark: str,
    source_bot_name: str,
    request_id: str,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    action_text = str(action or "").strip().lower()
    if action_text in {"充值", "credit"}:
        ledger_action = BalanceAction.CREDIT
    elif action_text in {"扣款", "debit"}:
        ledger_action = BalanceAction.DEBIT
    else:
        raise ValueError("Unsupported balance action.")

    amount_value = _normalize_amount(amount)
    if amount_value <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero.")

    request_text = str(request_id or "").strip()
    if not request_text:
        request_text = f"user-balance-{user_id}-{datetime.now():%Y%m%d%H%M%S%f}"

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        existing = session.exec(
            select(BalanceLedger).where(BalanceLedger.request_id == request_text)
        ).first()
        if existing is not None:
            existing_user = session.exec(select(User).where(User.id == int(existing.user_id))).first()
            if existing_user is None:
                raise ValueError("User not found.")
            account = None
            if existing.bot_id:
                account = session.exec(
                    select(BotUserAccount)
                    .where(BotUserAccount.user_id == int(existing.user_id))
                    .where(BotUserAccount.bot_id == int(existing.bot_id))
                ).first()
            return {
                "id": int(existing_user.id or 0),
                "balance": round(float(account.balance if account else existing_user.balance or 0), 2),
                "total_deposit": round(float(account.total_deposit if account else existing_user.total_deposit or 0), 2),
                "user_balance": round(float(existing_user.balance or 0), 2),
                "user_total_deposit": round(float(existing_user.total_deposit or 0), 2),
                "request_id": request_text,
            }

        user = session.exec(select(User).where(User.id == int(user_id))).first()
        if user is None:
            raise ValueError("User not found.")

        bot_map = {int(item.id or 0): item for item in session.exec(select(BotInstance)).all()}
        bot = _resolve_bot(
            user=user,
            source_bot_name=source_bot_name,
            bot_map=bot_map,
            session=session,
        )
        if bot is None:
            raise ValueError("Bot not found.")
        account = _ensure_bot_account(session, user=user, bot=bot)

        operator = session.exec(
            select(AdminUser).where(AdminUser.username == str(operator_username or "").strip())
        ).first()

        before_balance = _normalize_amount(account.balance or 0)
        if ledger_action == BalanceAction.DEBIT and amount_value > before_balance:
            raise ValueError("Amount exceeds current balance.")

        if ledger_action == BalanceAction.CREDIT:
            after_balance = _normalize_amount(before_balance + amount_value)
            account.total_deposit = _normalize_amount(account.total_deposit or 0) + amount_value
        else:
            after_balance = _normalize_amount(before_balance - amount_value)

        account.balance = after_balance
        account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        account.last_active_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(account)

        _sync_user_aggregate_from_accounts(session, user=user)

        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                action=ledger_action,
                amount=amount_value,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=int(operator.id or 0) if operator else None,
                remark=str(remark or ""),
                request_id=request_text,
            )
        )

        session.add(
            AdminAuditLog(
                operator_id=int(operator.id or 0) if operator else None,
                action="users.balance_adjust",
                target_type="user",
                target_id=int(user.id or 0),
                request_id=request_text,
                detail_json=(
                    '{"user_id":%d,"action":"%s","amount":"%s","source_bot":"%s"}'
                    % (
                        int(user.id or 0),
                        ledger_action.value,
                        str(amount_value),
                        str(source_bot_name or "").replace('"', "'"),
                    )
                ),
            )
        )

        session.commit()
        session.refresh(user)
        session.refresh(account)
        return {
            "id": int(user.id or 0),
            "balance": round(float(account.balance or 0), 2),
            "total_deposit": round(float(account.total_deposit or 0), 2),
            "user_balance": round(float(user.balance or 0), 2),
            "user_total_deposit": round(float(user.total_deposit or 0), 2),
            "request_id": request_text,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
