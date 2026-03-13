"""Runtime identity helpers for binding Telegram users to DB rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def ensure_runtime_identity(
    *,
    bot_token: str,
    bot_name: str | None,
    bot_username: str | None,
    tg_user: Any,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    """Ensure bot row and mapped user row exist for runtime handlers."""
    token_text = str(bot_token or "").strip()
    if not token_text:
        raise ValueError("bot_token is required.")

    telegram_id = int(getattr(tg_user, "id", 0) or 0)
    if telegram_id <= 0:
        raise ValueError("tg_user.id is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        now = _now()
        is_new_bot = False
        is_new_user = False

        bot = session.exec(select(BotInstance).where(BotInstance.token == token_text)).first()
        resolved_name = _as_text(bot_name) or _as_text(bot_username) or "Runtime Bot"
        resolved_username = _as_text(bot_username)

        if bot is None:
            bot = BotInstance(
                token=token_text,
                name=resolved_name,
                username=resolved_username,
                status=BotStatus.ACTIVE,
                is_enabled=True,
                is_platform_bot=True,
                created_at=now,
                updated_at=now,
                last_active_at=now,
            )
            session.add(bot)
            session.flush()
            is_new_bot = True
        else:
            if resolved_name and bot.name != resolved_name:
                bot.name = resolved_name
            if resolved_username and bot.username != resolved_username:
                bot.username = resolved_username
            bot.status = BotStatus.ACTIVE
            bot.is_enabled = True
            bot.updated_at = now
            bot.last_active_at = now
            session.add(bot)

        # flush 后 bot.id 必须有值，否则后续写入 from_bot_id 会静默为 0
        if not bot.id:
            raise RuntimeError("BotInstance.id is not assigned after flush; check DB constraints.")
        bot_id = int(bot.id)

        user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        username = _as_text(getattr(tg_user, "username", None))
        first_name = _as_text(getattr(tg_user, "first_name", None))
        last_name = _as_text(getattr(tg_user, "last_name", None))
        language_code = _as_text(getattr(tg_user, "language_code", None)) or "zh"

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                from_bot_id=bot_id,
                is_banned=False,
                created_at=now,
                updated_at=now,
                last_active_at=now,
            )
            session.add(user)
            session.flush()
            is_new_user = True
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.from_bot_id = bot_id
            user.updated_at = now
            user.last_active_at = now
            session.add(user)

        account = session.exec(
            select(BotUserAccount)
            .where(BotUserAccount.user_id == int(user.id or 0))
            .where(BotUserAccount.bot_id == int(bot_id))
        ).first()
        if account is None:
            has_any_account = session.exec(
                select(BotUserAccount.id).where(BotUserAccount.user_id == int(user.id or 0))
            ).first()
            account = BotUserAccount(
                user_id=int(user.id or 0),
                bot_id=int(bot_id),
                balance=user.balance if has_any_account is None else 0,
                total_deposit=user.total_deposit if has_any_account is None else 0,
                total_spent=user.total_spent if has_any_account is None else 0,
                order_count=0,
                created_at=now,
                updated_at=now,
                last_active_at=now,
            )
        else:
            account.updated_at = now
            account.last_active_at = now
        session.add(account)

        session.commit()
        session.refresh(bot)
        session.refresh(user)
        return {
            "bot_id": bot_id,
            "user_id": int(user.id),
            "is_new_bot": is_new_bot,
            "is_new_user": is_new_user,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
