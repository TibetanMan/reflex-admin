from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.system_setting import SystemSetting
from shared.models.wallet import WalletAddress


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "settings_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_admin(session_factory):
    session = session_factory()
    admin = AdminUser(
        username="admin",
        email="admin@local.test",
        password_hash="",
        role=AdminRole.SUPER_ADMIN,
        display_name="Super Admin",
        is_active=True,
        is_verified=True,
    )
    admin.set_password("admin123")
    session.add(admin)
    session.commit()
    session.close()


def test_settings_snapshot_returns_defaults_when_db_empty(tmp_path: Path):
    from services.settings_service import get_settings_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_admin(session_factory)

    snapshot = get_settings_snapshot(session_factory=session_factory)
    assert snapshot["default_usdt_address"] != ""
    assert str(snapshot["usdt_query_api_url"]).startswith("http")
    assert str(snapshot["bins_query_api_url"]).startswith("http")
    assert snapshot["telegram_push_enabled"] in {True, False}


def test_settings_updates_are_persisted_to_system_settings(tmp_path: Path):
    from services.settings_service import (
        get_settings_snapshot,
        update_bins_query_api_settings,
        update_default_usdt_address,
        update_telegram_push_settings,
        update_usdt_query_api_settings,
    )

    session_factory = _session_factory(tmp_path)
    _seed_admin(session_factory)

    update_default_usdt_address(
        address="TNEWUSDTADDRESS000001",
        operator_username="admin",
        session_factory=session_factory,
    )
    update_usdt_query_api_settings(
        api_url="https://example.test/usdt",
        api_key="usdt-key",
        timeout_seconds=12,
        operator_username="admin",
        session_factory=session_factory,
    )
    update_bins_query_api_settings(
        api_url="https://example.test/bins",
        api_key="bins-key",
        timeout_seconds=15,
        operator_username="admin",
        session_factory=session_factory,
    )
    update_telegram_push_settings(
        enabled=True,
        bot_token="bot-token",
        chat_id="chat-id",
        push_interval_seconds=9,
        max_messages_per_minute=40,
        retry_times=2,
        operator_username="admin",
        session_factory=session_factory,
    )

    snapshot = get_settings_snapshot(session_factory=session_factory)
    assert snapshot["default_usdt_address"] == "TNEWUSDTADDRESS000001"
    assert snapshot["usdt_query_api_url"] == "https://example.test/usdt"
    assert snapshot["usdt_query_api_key"] == "usdt-key"
    assert snapshot["usdt_query_api_timeout_seconds"] == 12
    assert snapshot["bins_query_api_url"] == "https://example.test/bins"
    assert snapshot["bins_query_api_key"] == "bins-key"
    assert snapshot["bins_query_api_timeout_seconds"] == 15
    assert snapshot["telegram_push_enabled"] is True
    assert snapshot["telegram_bot_token"] == "bot-token"
    assert snapshot["telegram_chat_id"] == "chat-id"
    assert snapshot["telegram_push_interval_seconds"] == 9
    assert snapshot["telegram_max_messages_per_minute"] == 40
    assert snapshot["telegram_retry_times"] == 2

    session = session_factory()
    keys = sorted(item.key for item in session.exec(select(SystemSetting)).all())
    session.close()
    assert keys == sorted(
        [
            "settings.bins_query_api",
            "settings.default_usdt_address",
            "settings.telegram_push",
            "settings.usdt_query_api",
        ]
    )


def test_update_default_usdt_address_syncs_platform_wallet(tmp_path: Path):
    from services.settings_service import update_default_usdt_address

    session_factory = _session_factory(tmp_path)
    _seed_admin(session_factory)

    update_default_usdt_address(
        address="TDEFAULTSYNC000001",
        operator_username="admin",
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        wallet = session.exec(
            select(WalletAddress).where(WalletAddress.address == "TDEFAULTSYNC000001")
        ).first()
    finally:
        session.close()

    assert wallet is not None
    assert bool(wallet.is_platform) is True
