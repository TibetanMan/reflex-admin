from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.user import User


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "bot_runtime_context.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


@dataclass
class _TelegramUser:
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


def test_ensure_runtime_identity_creates_bot_and_user(tmp_path: Path):
    from bot.runtime_context import ensure_runtime_identity

    session_factory = _session_factory(tmp_path)
    tg_user = _TelegramUser(
        id=9001001,
        username="first_user",
        first_name="First",
        last_name="User",
        language_code="zh-hans",
    )

    result = ensure_runtime_identity(
        bot_token="token-a",
        bot_name="Runtime Bot A",
        bot_username="runtime_bot_a",
        tg_user=tg_user,
        session_factory=session_factory,
    )

    assert result["bot_id"] > 0
    assert result["user_id"] > 0
    assert result["is_new_bot"] is True
    assert result["is_new_user"] is True

    session = session_factory()
    try:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(result["bot_id"]))).first()
        user = session.exec(select(User).where(User.id == int(result["user_id"]))).first()
        assert bot is not None
        assert user is not None
        assert bot.status == BotStatus.ACTIVE
        assert bot.is_enabled is True
        assert user.telegram_id == 9001001
        assert user.from_bot_id == int(bot.id or 0)
    finally:
        session.close()


def test_ensure_runtime_identity_reuses_rows_and_updates_user_profile(tmp_path: Path):
    from bot.runtime_context import ensure_runtime_identity

    session_factory = _session_factory(tmp_path)

    first = ensure_runtime_identity(
        bot_token="token-a",
        bot_name="Runtime Bot A",
        bot_username="runtime_bot_a",
        tg_user=_TelegramUser(
            id=9001002,
            username="old_name",
            first_name="Old",
            last_name="Name",
            language_code="zh",
        ),
        session_factory=session_factory,
    )
    second = ensure_runtime_identity(
        bot_token="token-a",
        bot_name="Runtime Bot A",
        bot_username="runtime_bot_a",
        tg_user=_TelegramUser(
            id=9001002,
            username="new_name",
            first_name="New",
            last_name="Name",
            language_code="en",
        ),
        session_factory=session_factory,
    )

    assert first["bot_id"] == second["bot_id"]
    assert first["user_id"] == second["user_id"]
    assert second["is_new_bot"] is False
    assert second["is_new_user"] is False

    session = session_factory()
    try:
        rows = list(session.exec(select(User).where(User.telegram_id == 9001002)).all())
        assert len(rows) == 1
        assert rows[0].username == "new_name"
        assert rows[0].first_name == "New"
        assert rows[0].language_code == "en"
    finally:
        session.close()


def test_ensure_runtime_identity_creates_bot_scoped_accounts_for_same_user(tmp_path: Path):
    from bot.runtime_context import ensure_runtime_identity
    from shared.models.bot_user_account import BotUserAccount

    session_factory = _session_factory(tmp_path)

    first = ensure_runtime_identity(
        bot_token="token-a",
        bot_name="Runtime Bot A",
        bot_username="runtime_bot_a",
        tg_user=_TelegramUser(
            id=9001999,
            username="same_user",
            first_name="Same",
            last_name="User",
            language_code="zh",
        ),
        session_factory=session_factory,
    )
    second = ensure_runtime_identity(
        bot_token="token-b",
        bot_name="Runtime Bot B",
        bot_username="runtime_bot_b",
        tg_user=_TelegramUser(
            id=9001999,
            username="same_user",
            first_name="Same",
            last_name="User",
            language_code="zh",
        ),
        session_factory=session_factory,
    )

    assert first["user_id"] == second["user_id"]
    assert first["bot_id"] != second["bot_id"]

    session = session_factory()
    try:
        accounts = list(
            session.exec(
                select(BotUserAccount)
                .where(BotUserAccount.user_id == int(first["user_id"]))
                .order_by(BotUserAccount.bot_id.asc())
            ).all()
        )
        assert len(accounts) == 2
        assert int(accounts[0].bot_id) == int(first["bot_id"])
        assert int(accounts[1].bot_id) == int(second["bot_id"])
    finally:
        session.close()
