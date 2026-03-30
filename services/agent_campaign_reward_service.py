"""Reward settlement for agent first-deposit campaigns."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from services.agent_campaign_service import campaign_status_text
from shared.database import get_db_session
from shared.models.agent_campaign import AgentCampaignConfig, CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit, DepositStatus
from shared.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _status_text(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value or "")


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ensure_bot_account(session: Session, *, user_id: int, bot_id: int) -> BotUserAccount:
    account = session.exec(
        select(BotUserAccount)
        .where(BotUserAccount.user_id == int(user_id))
        .where(BotUserAccount.bot_id == int(bot_id))
    ).first()
    if account is not None:
        return account

    account = BotUserAccount(
        user_id=int(user_id),
        bot_id=int(bot_id),
        balance=_money(0),
        total_deposit=_money(0),
        total_spent=_money(0),
        order_count=0,
        created_at=_now(),
        updated_at=_now(),
        last_active_at=_now(),
    )
    session.add(account)
    session.flush()
    return account


def _active_campaign_for_bot(
    session: Session,
    *,
    bot_id: int,
    now: datetime,
) -> Optional[AgentCampaignConfig]:
    bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
    if bot is None or bot.owner_agent_id is None:
        return None

    row = session.exec(
        select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(bot.owner_agent_id))
    ).first()
    if row is None:
        return None
    if campaign_status_text(row, now=now) != "active":
        return None
    return row


def apply_agent_campaign_reward_for_deposit(
    *,
    deposit_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
    session: Optional[Session] = None,
) -> dict[str, Any]:
    owns_session = session is None
    current_session = session if session is not None else (session_factory or get_db_session)()
    try:
        deposit = current_session.get(Deposit, int(deposit_id))
        if deposit is None or _status_text(deposit.status) != DepositStatus.COMPLETED.value:
            return {"granted": False, "reason": "deposit_not_completed"}

        at_time = deposit.completed_at or deposit.updated_at or _now()
        campaign = _active_campaign_for_bot(current_session, bot_id=int(deposit.bot_id), now=at_time)
        if campaign is None:
            return {"granted": False, "reason": "campaign_inactive"}

        existing = current_session.exec(
            select(CampaignRewardGrant)
            .where(CampaignRewardGrant.user_id == int(deposit.user_id))
            .where(CampaignRewardGrant.bot_id == int(deposit.bot_id))
            .where(CampaignRewardGrant.grant_type == "first_deposit")
        ).first()
        if existing is not None:
            return {"granted": False, "reason": "already_granted"}

        first_completed = current_session.exec(
            select(Deposit)
            .where(Deposit.user_id == int(deposit.user_id))
            .where(Deposit.bot_id == int(deposit.bot_id))
            .where(Deposit.status == DepositStatus.COMPLETED)
            .order_by(Deposit.completed_at.asc(), Deposit.id.asc())
        ).first()
        if first_completed is None or int(first_completed.id or 0) != int(deposit.id or 0):
            return {"granted": False, "reason": "not_first_completed_deposit"}

        base_amount = _money(deposit.actual_amount or deposit.amount or 0)
        rate_value = Decimal(str(campaign.first_deposit_bonus_rate or 0))
        fixed_value = _money(campaign.first_deposit_bonus_amount or 0)
        bonus_amount = _money(base_amount * rate_value + fixed_value)
        if bonus_amount <= Decimal("0.00"):
            return {"granted": False, "reason": "bonus_zero"}

        user = current_session.exec(select(User).where(User.id == int(deposit.user_id))).first()
        if user is None:
            return {"granted": False, "reason": "user_not_found"}

        account = _ensure_bot_account(
            current_session,
            user_id=int(user.id or 0),
            bot_id=int(deposit.bot_id),
        )

        before_balance = _money(account.balance or 0)
        after_balance = _money(before_balance + bonus_amount)
        account.balance = after_balance
        account.updated_at = _now()
        account.last_active_at = _now()
        current_session.add(account)

        user.balance = _money(user.balance or 0) + bonus_amount
        user.updated_at = _now()
        current_session.add(user)

        current_session.add(
            CampaignRewardGrant(
                campaign_config_id=int(campaign.id or 0),
                user_id=int(user.id or 0),
                bot_id=int(deposit.bot_id),
                grant_type="first_deposit",
                reward_amount=bonus_amount,
                granted_at=_now(),
                operator_id=None,
                remark=f"deposit_id={int(deposit.id or 0)}",
            )
        )

        current_session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(deposit.bot_id),
                action=BalanceAction.CAMPAIGN_BONUS,
                amount=bonus_amount,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=None,
                remark="agent_campaign_first_deposit_bonus",
                request_id=f"campaign-bonus-{int(deposit.id or 0)}",
            )
        )

        if owns_session:
            current_session.commit()
        else:
            current_session.flush()
        return {
            "granted": True,
            "reason": "granted",
            "bonus_amount": float(bonus_amount),
            "campaign_config_id": int(campaign.id or 0),
        }
    except Exception:
        if owns_session:
            current_session.rollback()
        raise
    finally:
        if owns_session:
            current_session.close()
