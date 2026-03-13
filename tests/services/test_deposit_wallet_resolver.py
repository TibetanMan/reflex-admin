from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.wallet import WalletAddress, WalletStatus


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "deposit_wallet_resolver.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_bot_and_wallets(session_factory):
    session = session_factory()
    try:
        bot_one = BotInstance(
            token="resolver-bot-token-001",
            name="Resolver Bot One",
            username="resolver_bot_one",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=True,
            usdt_address="TRX_BOT_1",
        )
        bot_two = BotInstance(
            token="resolver-bot-token-002",
            name="Resolver Bot Two",
            username="resolver_bot_two",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_2",
        )
        bot_three = BotInstance(
            token="resolver-bot-token-003",
            name="Resolver Bot Three",
            username="resolver_bot_three",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=False,
            usdt_address="TRX_BOT_3",
        )
        session.add(bot_one)
        session.add(bot_two)
        session.add(bot_three)
        session.commit()
        session.refresh(bot_one)
        session.refresh(bot_two)
        session.refresh(bot_three)

        session.add(
            WalletAddress(
                address="TRX_WALLET_BOT_1",
                bot_id=int(bot_one.id or 0),
                status=WalletStatus.ACTIVE,
                label="Wallet Bot One",
            )
        )
        session.add(
            WalletAddress(
                address="TRX_WALLET_BOT_2",
                bot_id=int(bot_two.id or 0),
                status=WalletStatus.ACTIVE,
                label="Wallet Bot Two",
            )
        )
        session.add(
            WalletAddress(
                address="TRX_WALLET_BOT_3",
                bot_id=int(bot_three.id or 0),
                status=WalletStatus.INACTIVE,
                label="Wallet Bot Three",
            )
        )
        session.commit()
    finally:
        session.close()


def test_resolve_wallet_by_bot_returns_target_wallet(tmp_path: Path):
    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise

    session_factory = _session_factory(tmp_path)
    _seed_bot_and_wallets(session_factory)

    session = session_factory()
    try:
        wallet = resolve_wallet_by_bot_or_raise(session, bot_id=2)
        assert int(wallet.bot_id or 0) == 2
        assert str(wallet.address) == "TRX_WALLET_BOT_2"
    finally:
        session.close()


def test_resolve_wallet_by_bot_raises_when_missing(tmp_path: Path):
    import pytest

    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise

    session_factory = _session_factory(tmp_path)
    _seed_bot_and_wallets(session_factory)

    session = session_factory()
    try:
        with pytest.raises(ValueError, match="wallet"):
            resolve_wallet_by_bot_or_raise(session, bot_id=9)
    finally:
        session.close()


def test_resolve_wallet_by_bot_raises_when_inactive(tmp_path: Path):
    import pytest

    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise

    session_factory = _session_factory(tmp_path)
    _seed_bot_and_wallets(session_factory)

    session = session_factory()
    try:
        with pytest.raises(ValueError, match="active"):
            resolve_wallet_by_bot_or_raise(session, bot_id=3)
    finally:
        session.close()
