from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.order import Order, OrderStatus
from shared.models.user import User
from shared.models.user_export import UserBotSource


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "bot_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def _seed_rows(session_factory):
    session = session_factory()

    agent_admin = AdminUser(
        username="agent1",
        email="agent1@local.test",
        password_hash="",
        role=AdminRole.AGENT,
        display_name="Agent One",
        is_active=True,
        is_verified=True,
    )
    agent_admin.set_password("agent123")
    session.add(agent_admin)
    session.commit()
    session.refresh(agent_admin)

    agent = Agent(
        admin_user_id=int(agent_admin.id or 0),
        name="Agent One",
        is_active=True,
        is_verified=True,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)

    session.add(
        BotInstance(
            token="platform-bot-token-001",
            name="Platform Bot",
            username="platform_bot",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            is_platform_bot=True,
            total_users=3,
            total_orders=4,
            total_revenue=15.5,
        )
    )
    session.add(
        BotInstance(
            token="agent-bot-token-001",
            name="Agent Bot",
            username="agent_bot",
            status=BotStatus.INACTIVE,
            is_enabled=False,
            is_platform_bot=False,
            owner_agent_id=int(agent.id or 0),
            total_users=8,
            total_orders=10,
            total_revenue=55.0,
        )
    )
    session.commit()
    session.close()


def test_list_bots_snapshot_and_owner_options(tmp_path: Path):
    from services.bot_service import list_bot_owner_options, list_bots_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    rows = list_bots_snapshot(session_factory=session_factory)
    owners = list_bot_owner_options(session_factory=session_factory)

    assert len(rows) == 2
    assert rows[0]["name"] in {"Platform Bot", "Agent Bot"}
    assert any(row["owner"] == "平台自营" for row in rows)
    assert any(row["owner"] == "Agent One" for row in rows)
    assert owners[0] == "平台自营"
    assert "Agent One" in owners
    assert any(bool(row.get("runtime_selected")) for row in rows)


def test_create_toggle_update_delete_bot_flow(tmp_path: Path):
    from services.bot_service import (
        create_bot_record,
        delete_bot_record,
        list_bots_snapshot,
        toggle_bot_record_status,
        update_bot_record,
    )

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    payload = create_bot_record(
        name="Created Bot",
        token="created-bot-token-xyz",
        owner_name="平台自营",
        usdt_address="TRX_CREATED",
        session_factory=session_factory,
    )
    assert payload["name"] == "Created Bot"
    assert payload["status"] == "inactive"

    toggled = toggle_bot_record_status(bot_id=int(payload["id"]), session_factory=session_factory)
    assert toggled["status"] == "active"

    rows_after_toggle = list_bots_snapshot(session_factory=session_factory)
    assert sum(1 for row in rows_after_toggle if row["status"] == "active") == 2

    updated = update_bot_record(
        bot_id=int(payload["id"]),
        name="Updated Bot",
        owner_name="平台自营",
        usdt_address="TRX_UPDATED",
        session_factory=session_factory,
    )
    assert updated["name"] == "Updated Bot"
    assert updated["usdt_address"] == "TRX_UPDATED"

    delete_bot_record(bot_id=int(payload["id"]), session_factory=session_factory)
    rows = list_bots_snapshot(session_factory=session_factory)
    assert all(row["id"] != int(payload["id"]) for row in rows)

    session = session_factory()
    assert session.exec(select(BotInstance).where(BotInstance.name == "Updated Bot")).first() is None
    session.close()


def test_get_bot_snapshot_returns_single_row(tmp_path: Path):
    from services.bot_service import get_bot_snapshot

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    row = get_bot_snapshot(bot_id=1, session_factory=session_factory)
    assert row["id"] == 1
    assert row["name"] in {"Platform Bot", "Agent Bot"}


def test_resolve_runtime_bot_binding_prefers_active_platform_bot(tmp_path: Path):
    from services.bot_service import list_runtime_bot_bindings, resolve_runtime_bot_binding

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    row = resolve_runtime_bot_binding(session_factory=session_factory)
    assert row["name"] == "Platform Bot"
    assert row["source"] == "database"
    assert row["token"]

    rows = list_runtime_bot_bindings(session_factory=session_factory)
    assert len(rows) == 1
    assert rows[0]["name"] == "Platform Bot"


def test_delete_bot_record_rebinds_required_relations(tmp_path: Path):
    from services.bot_service import delete_bot_record

    session_factory = _session_factory(tmp_path)
    _seed_rows(session_factory)

    session = session_factory()
    try:
        user = User(
            telegram_id=9001001001,
            username="buyer_a",
            first_name="Buyer",
            from_bot_id=1,
            balance=10,
            total_deposit=10,
            total_spent=0,
            is_banned=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(
            Order(
                order_no="BOT-SVC-ORDER-1",
                user_id=int(user.id or 0),
                bot_id=1,
                total_amount=1,
                paid_amount=1,
                items_count=1,
                status=OrderStatus.COMPLETED,
                platform_profit=0,
                agent_profit=0,
                supplier_profit=0,
            )
        )
        session.add(
            Deposit(
                deposit_no="BOT-SVC-DEP-1",
                user_id=int(user.id or 0),
                bot_id=1,
                amount=1,
                actual_amount=1,
                method=DepositMethod.MANUAL,
                to_address="TRX_TEST",
                status=DepositStatus.COMPLETED,
            )
        )
        session.add(
            UserBotSource(
                user_id=int(user.id or 0),
                bot_id=1,
                is_primary=True,
            )
        )
        session.commit()
    finally:
        session.close()

    delete_bot_record(bot_id=1, session_factory=session_factory)

    session = session_factory()
    try:
        assert session.exec(select(BotInstance).where(BotInstance.id == 1)).first() is None
        order = session.exec(select(Order).where(Order.order_no == "BOT-SVC-ORDER-1")).first()
        deposit = session.exec(select(Deposit).where(Deposit.deposit_no == "BOT-SVC-DEP-1")).first()
        source = session.exec(select(UserBotSource).where(UserBotSource.user_id == 1)).first()
        assert order is not None and int(order.bot_id) == 2
        assert deposit is not None and int(deposit.bot_id) == 2
        assert source is not None and int(source.bot_id) == 2
    finally:
        session.close()
