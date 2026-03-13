"""Synchronize configured USDT addresses into wallet source-of-truth rows."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from shared.models.bot_instance import BotInstance
from shared.models.system_setting import SystemSetting
from shared.models.wallet import WalletAddress, WalletStatus


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_address(value: str) -> str:
    return str(value or "").strip()


def sync_bot_wallet_from_address(session: Session, *, bot: BotInstance) -> bool:
    """Ensure a bot-configured USDT address is represented in wallet table."""
    address_text = _normalize_address(str(bot.usdt_address or ""))
    if not address_text:
        return False

    changed = False
    bot_id = int(bot.id or 0)
    if bot_id <= 0:
        return False

    wallets_bound_to_bot = list(
        session.exec(
            select(WalletAddress)
            .where(WalletAddress.bot_id == bot_id)
            .order_by(WalletAddress.id.asc())
        ).all()
    )
    target = session.exec(
        select(WalletAddress).where(WalletAddress.address == address_text)
    ).first()

    for row in wallets_bound_to_bot:
        if str(row.address) == address_text:
            continue
        row.bot_id = None
        if row.status == WalletStatus.ACTIVE:
            row.status = WalletStatus.INACTIVE
        row.updated_at = _now()
        session.add(row)
        changed = True

    if target is None:
        target = WalletAddress(
            address=address_text,
            bot_id=bot_id,
            is_platform=bool(bot.is_platform_bot),
            status=WalletStatus.ACTIVE,
            label=f"{str(bot.name or 'Bot')} 收款地址",
            balance=0,
            total_received=0,
            updated_at=_now(),
        )
        session.add(target)
        return True

    if int(target.bot_id or 0) != bot_id:
        target.bot_id = bot_id
        changed = True
    desired_is_platform = bool(bot.is_platform_bot)
    if bool(target.is_platform) != desired_is_platform:
        target.is_platform = desired_is_platform
        changed = True
    if target.status != WalletStatus.ACTIVE:
        target.status = WalletStatus.ACTIVE
        changed = True
    desired_label = f"{str(bot.name or 'Bot')} 收款地址"
    if str(target.label or "") != desired_label:
        target.label = desired_label
        changed = True
    if changed:
        target.updated_at = _now()
        session.add(target)
    return changed


def sync_default_wallet_from_settings(session: Session) -> bool:
    """Ensure settings.default_usdt_address is represented as platform wallet."""
    setting = session.exec(
        select(SystemSetting).where(SystemSetting.key == "settings.default_usdt_address")
    ).first()
    if setting is None:
        return False

    try:
        payload = json.loads(str(setting.value_json or "{}"))
    except json.JSONDecodeError:
        payload = {}
    address_text = _normalize_address(str(payload.get("value") or ""))
    if not address_text:
        return False

    target = session.exec(
        select(WalletAddress).where(WalletAddress.address == address_text)
    ).first()
    if target is None:
        session.add(
            WalletAddress(
                address=address_text,
                bot_id=None,
                is_platform=True,
                status=WalletStatus.ACTIVE,
                label="默认USDT收款地址",
                balance=0,
                total_received=0,
                updated_at=_now(),
            )
        )
        return True

    changed = False
    if not bool(target.is_platform):
        target.is_platform = True
        changed = True
    if target.status != WalletStatus.ACTIVE:
        target.status = WalletStatus.ACTIVE
        changed = True
    if not str(target.label or "").strip():
        target.label = "默认USDT收款地址"
        changed = True
    if changed:
        target.updated_at = _now()
        session.add(target)
    return changed


def sync_wallets_from_config(session: Session) -> bool:
    """Backfill wallet rows from current bot/settings configured addresses."""
    changed = sync_default_wallet_from_settings(session)
    bots = list(session.exec(select(BotInstance).order_by(BotInstance.id.asc())).all())
    for bot in bots:
        changed = sync_bot_wallet_from_address(session, bot=bot) or changed
    return changed
