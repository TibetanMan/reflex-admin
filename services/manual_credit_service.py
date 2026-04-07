from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlmodel import Session, select

from services.business_stats_service import sync_bot_and_related_agent_fields
from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _next_deposit_no(session: Session) -> str:
    prefix = datetime.now().strftime("DEP%Y%m%d%H%M%S")
    candidate = prefix
    suffix = 1
    while session.exec(select(Deposit).where(Deposit.deposit_no == candidate)).first() is not None:
        suffix += 1
        candidate = f"{prefix}{suffix:02d}"
    return candidate


def _ensure_bot_account(session: Session, *, user: User, bot: BotInstance) -> BotUserAccount:
    account = session.exec(
        select(BotUserAccount)
        .where(BotUserAccount.user_id == int(user.id or 0))
        .where(BotUserAccount.bot_id == int(bot.id or 0))
    ).first()
    if account is not None:
        return account

    has_any = session.exec(select(BotUserAccount.id).where(BotUserAccount.user_id == int(user.id or 0))).first()
    seed_balance = _money(user.balance or 0) if has_any is None else Decimal("0.00")
    seed_total_deposit = _money(user.total_deposit or 0) if has_any is None else Decimal("0.00")
    seed_total_spent = _money(user.total_spent or 0) if has_any is None else Decimal("0.00")

    account = BotUserAccount(
        user_id=int(user.id or 0),
        bot_id=int(bot.id or 0),
        balance=seed_balance,
        total_deposit=seed_total_deposit,
        total_spent=seed_total_spent,
        order_count=0,
        is_banned=False,
        ban_reason=None,
        created_at=_now(),
        updated_at=_now(),
        last_active_at=user.last_active_at,
    )
    session.add(account)
    session.flush()
    sync_bot_and_related_agent_fields(session, bot_id=int(bot.id or 0))
    return account


def _sync_user_aggregate_from_accounts(session: Session, *, user: User) -> None:
    rows = list(session.exec(select(BotUserAccount).where(BotUserAccount.user_id == int(user.id or 0))).all())
    if not rows:
        return
    user.balance = _money(sum(float(item.balance or 0) for item in rows))
    user.total_deposit = _money(sum(float(item.total_deposit or 0) for item in rows))
    user.total_spent = _money(sum(float(item.total_spent or 0) for item in rows))
    user.updated_at = _now()
    session.add(user)


def create_manual_credit(
    session: Session,
    *,
    user: User,
    bot: BotInstance,
    amount: Decimal | float | int | str,
    remark: str,
    operator: Optional[AdminUser],
    ledger_action: BalanceAction,
    request_id: str,
    audit_action: str,
    audit_detail_json: str,
) -> dict[str, object]:
    amount_value = _money(amount)
    if amount_value <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero.")

    wallet = resolve_wallet_by_bot_or_raise(session, bot_id=int(bot.id or 0))
    account = _ensure_bot_account(session, user=user, bot=bot)

    before_balance = _money(account.balance or 0)
    after_balance = _money(before_balance + amount_value)

    account.balance = after_balance
    account.total_deposit = _money(account.total_deposit or 0) + amount_value
    account.updated_at = _now()
    account.last_active_at = _now()
    session.add(account)

    _sync_user_aggregate_from_accounts(session, user=user)

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
        completed_at=_now(),
    )
    session.add(deposit)

    wallet.balance = _money(wallet.balance or 0) + amount_value
    wallet.total_received = _money(wallet.total_received or 0) + amount_value
    wallet.updated_at = _now()
    session.add(wallet)

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
            request_id=str(request_id or "").strip() or None,
        )
    )

    session.add(
        AdminAuditLog(
            operator_id=int(operator.id or 0) if operator else None,
            action=audit_action,
            target_type="user",
            target_id=int(user.id or 0),
            request_id=str(request_id or "").strip() or None,
            detail_json=str(audit_detail_json or "{}"),
        )
    )

    session.flush()
    return {
        "deposit": deposit,
        "account": account,
        "wallet": wallet,
        "before_balance": before_balance,
        "after_balance": after_balance,
    }
