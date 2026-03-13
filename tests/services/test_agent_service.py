from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from shared.models.admin_user import AdminUser
from shared.models.agent import Agent
from shared.models.bot_instance import BotInstance


def _session_factory(tmp_path: Path):
    db_file = tmp_path / "agent_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _new_session() -> Session:
        return Session(engine)

    return _new_session


def test_create_list_update_toggle_agent_flow(tmp_path: Path):
    from services.agent_service import (
        create_agent_with_bot,
        list_agents_snapshot,
        toggle_agent_record_status,
        update_agent_record,
    )

    session_factory = _session_factory(tmp_path)
    created = create_agent_with_bot(
        name="Agent A",
        contact_telegram="@agent_a",
        contact_email="agent-a@example.com",
        bot_name="AgentA Bot",
        bot_token="agent-a-token-123",
        profit_rate=0.15,
        usdt_address="TRX_AGENT_A",
        session_factory=session_factory,
    )
    assert created["name"] == "Agent A"
    assert created["bot_name"] == "AgentA Bot"
    assert created["is_active"] is True

    rows = list_agents_snapshot(session_factory=session_factory)
    assert len(rows) == 1
    assert rows[0]["profit_rate_label"] == "15.00%"

    updated = update_agent_record(
        agent_id=int(created["id"]),
        name="Agent A+",
        contact_telegram="@agent_aplus",
        contact_email="agent-a-plus@example.com",
        bot_name="AgentA+ Bot",
        bot_token="agent-a-plus-token",
        profit_rate=0.2,
        usdt_address="TRX_AGENT_A_PLUS",
        is_verified=True,
        session_factory=session_factory,
    )
    assert updated["name"] == "Agent A+"
    assert updated["is_verified"] is True
    assert updated["profit_rate_label"] == "20.00%"

    toggled = toggle_agent_record_status(agent_id=int(created["id"]), session_factory=session_factory)
    assert toggled["is_active"] is False

    session = session_factory()
    assert session.exec(select(Agent)).first() is not None
    assert session.exec(select(AdminUser)).first() is not None
    assert session.exec(select(BotInstance)).first() is not None
    session.close()


def test_get_agent_snapshot_returns_single_row(tmp_path: Path):
    from services.agent_service import create_agent_with_bot, get_agent_snapshot

    session_factory = _session_factory(tmp_path)
    created = create_agent_with_bot(
        name="Agent Detail",
        contact_telegram="@agent_detail",
        contact_email="agent-detail@example.com",
        bot_name="AgentDetail Bot",
        bot_token="agent-detail-token",
        profit_rate=0.1,
        usdt_address="TRX_AGENT_DETAIL",
        session_factory=session_factory,
    )

    row = get_agent_snapshot(agent_id=int(created["id"]), session_factory=session_factory)
    assert row["id"] == int(created["id"])
    assert row["name"] == "Agent Detail"
