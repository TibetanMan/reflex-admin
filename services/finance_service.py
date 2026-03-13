"""Database-backed finance read/write services."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from services.deposit_chain_service import sync_pending_usdt_deposits
from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.user import User
from shared.models.wallet import WalletAddress


DepositFormatter = dict[str, Any]
WalletFormatter = dict[str, Any]

METHOD_LABELS = {
    DepositMethod.USDT_TRC20.value: "USDT TRC20",
    DepositMethod.USDT_ERC20.value: "USDT ERC20",
    DepositMethod.MANUAL.value: "手动充值",
}


def _display_user(user: Optional[User]) -> str:
    if user is None:
        return "-"
    if user.username:
        username = str(user.username)
        if not username.startswith("@"):
            username = f"@{username}"
        return f"{user.display_name} ({username})"
    return user.display_name


def _datetime_text(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _build_deposit_row(
    item: Deposit,
    *,
    user_map: dict[int, User],
    bot_map: dict[int, BotInstance],
) -> DepositFormatter:
    user = user_map.get(int(item.user_id))
    bot = bot_map.get(int(item.bot_id))
    status_value = item.status.value if hasattr(item.status, "value") else str(item.status)
    method_value = item.method.value if hasattr(item.method, "value") else str(item.method)
    return {
        "id": int(item.id or 0),
        "deposit_no": str(item.deposit_no),
        "user": _display_user(user),
        "user_id": int(item.user_id),
        "bot": str(bot.name if bot else f"Bot-{item.bot_id}"),
        "amount": float(item.amount),
        "actual_amount": float(item.actual_amount),
        "method": METHOD_LABELS.get(method_value, method_value),
        "to_address": str(item.to_address or "-"),
        "tx_hash": str(item.tx_hash) if item.tx_hash else None,
        "status": status_value,
        "created_at": _datetime_text(item.created_at) or "",
        "completed_at": _datetime_text(item.completed_at),
    }


def list_finance_deposits(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[DepositFormatter]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(session.exec(select(Deposit).order_by(Deposit.created_at.desc())).all())
        user_ids = {int(item.user_id) for item in rows}
        bot_ids = {int(item.bot_id) for item in rows}

        users = list(session.exec(select(User)).all())
        bots = list(session.exec(select(BotInstance)).all())
        user_map = {int(item.id or 0): item for item in users if int(item.id or 0) in user_ids}
        bot_map = {int(item.id or 0): item for item in bots if int(item.id or 0) in bot_ids}

        return [_build_deposit_row(item, user_map=user_map, bot_map=bot_map) for item in rows]
    finally:
        session.close()


def list_finance_wallets(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[WalletFormatter]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        wallets = list(session.exec(select(WalletAddress).order_by(WalletAddress.id.desc())).all())
        bot_map = {int(item.id or 0): item for item in session.exec(select(BotInstance)).all()}

        return [
            {
                "id": int(wallet.id or 0),
                "address": str(wallet.address),
                "label": str(wallet.label or "Wallet"),
                "bot": str(bot_map.get(int(wallet.bot_id or 0)).name if wallet.bot_id else "Platform"),
                "balance": float(wallet.balance),
                "total_received": float(wallet.total_received),
                "status": str(wallet.status.value if hasattr(wallet.status, "value") else wallet.status),
            }
            for wallet in wallets
        ]
    finally:
        session.close()


def get_finance_wallet(
    *,
    wallet_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> WalletFormatter:
    rows = list_finance_wallets(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(wallet_id):
            return row
    raise ValueError("Wallet not found.")


def reconcile_finance_deposits(
    *,
    limit: int = 100,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    return sync_pending_usdt_deposits(limit=limit, session_factory=session_factory)


def _find_user_by_identifier(session: Session, identifier: str) -> Optional[User]:
    text = str(identifier or "").strip()
    if not text:
        return None

    if text.isdigit():
        user = session.exec(select(User).where(User.telegram_id == int(text))).first()
        if user is not None:
            return user

    normalized = text.lstrip("@")
    return session.exec(select(User).where(User.username == normalized)).first()


def _next_deposit_no(session: Session) -> str:
    prefix = datetime.now().strftime("DEP%Y%m%d%H%M%S")
    candidate = prefix
    suffix = 1
    while session.exec(select(Deposit).where(Deposit.deposit_no == candidate)).first() is not None:
        suffix += 1
        candidate = f"{prefix}{suffix:02d}"
    return candidate


def create_manual_deposit(
    *,
    user_identifier: str,
    amount: Decimal,
    remark: str,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> DepositFormatter:
    amount_value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount_value <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _find_user_by_identifier(session, user_identifier)
        if user is None:
            raise ValueError("User not found.")

        bot = None
        if user.from_bot_id:
            bot = session.exec(select(BotInstance).where(BotInstance.id == int(user.from_bot_id))).first()
        if bot is None:
            bot = session.exec(select(BotInstance).order_by(BotInstance.id.asc())).first()
        if bot is None:
            raise ValueError("No bot instance available.")
        wallet = resolve_wallet_by_bot_or_raise(session, bot_id=int(bot.id or 0))

        operator = session.exec(
            select(AdminUser).where(AdminUser.username == str(operator_username or "").strip())
        ).first()

        before_balance = Decimal(str(user.balance or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        after_balance = (before_balance + amount_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        user.balance = after_balance
        user.total_deposit = (Decimal(str(user.total_deposit or 0)) + amount_value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(user)

        deposit = Deposit(
            deposit_no=_next_deposit_no(session),
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            amount=amount_value,
            actual_amount=amount_value,
            method=DepositMethod.MANUAL,
            to_address=str(wallet.address),
            status=DepositStatus.COMPLETED,
            operator_id=int(operator.id or 0) if operator else None,
            operator_remark=str(remark or "手动充值"),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(deposit)
        wallet.balance = (Decimal(str(wallet.balance or 0)) + amount_value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        wallet.total_received = (Decimal(str(wallet.total_received or 0)) + amount_value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        wallet.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(wallet)

        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                action=BalanceAction.MANUAL,
                amount=amount_value,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=int(operator.id or 0) if operator else None,
                remark=str(remark or "手动充值"),
                request_id=f"manual-{datetime.now():%Y%m%d%H%M%S%f}",
            )
        )

        session.add(
            AdminAuditLog(
                operator_id=int(operator.id or 0) if operator else None,
                action="finance.manual_deposit",
                target_type="user",
                target_id=int(user.id or 0),
                request_id=f"manual-deposit-{datetime.now():%Y%m%d%H%M%S%f}",
                detail_json=(
                    '{"user_identifier":"%s","amount":"%s","remark":"%s"}'
                    % (
                        str(user_identifier),
                        str(amount_value),
                        str(remark or ""),
                    )
                ),
            )
        )

        session.commit()
        session.refresh(deposit)

        user_map = {int(user.id or 0): user}
        bot_map = {int(bot.id or 0): bot}
        return _build_deposit_row(deposit, user_map=user_map, bot_map=bot_map)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
