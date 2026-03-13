"""Strict wallet resolution utilities for deposit creation paths."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from shared.models.wallet import WalletAddress, WalletStatus


def resolve_wallet_by_bot_or_raise(session: Session, *, bot_id: int) -> WalletAddress:
    """Return the first wallet bound to the target bot, or raise strict errors."""
    wallet: Optional[WalletAddress] = session.exec(
        select(WalletAddress)
        .where(WalletAddress.bot_id == int(bot_id))
        .order_by(WalletAddress.id.asc())
    ).first()

    if wallet is None:
        raise ValueError("Current bot has no configured receiving wallet.")

    status_text = str(wallet.status.value if hasattr(wallet.status, "value") else wallet.status)
    if status_text != WalletStatus.ACTIVE.value:
        raise ValueError("Current bot wallet is not active.")

    return wallet
