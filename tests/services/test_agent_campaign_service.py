from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from services.agent_campaign_service import (
    get_active_campaign_for_bot,
    upsert_agent_campaign_config,
)
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.agent_campaign import AgentCampaignConfig
from shared.models.bot_instance import BotInstance, BotStatus


def _build_session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'campaign_service.db'}")
    SQLModel.metadata.create_all(engine)
    return lambda: Session(engine)


def _seed_agent_and_bot(session_factory):
    session = session_factory()
    try:
        admin = AdminUser(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            role=AdminRole.SUPER_ADMIN,
            display_name="Admin",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        agent = Agent(
            admin_user_id=int(admin.id or 0),
            name="Agent One",
            profit_rate=0.1,
            is_active=True,
            is_verified=True,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        bot = BotInstance(
            token="123456:ABCDEF_campaign",
            name="Agent Bot",
            owner_agent_id=int(agent.id or 0),
            status=BotStatus.ACTIVE,
            is_enabled=True,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)
        return int(agent.id or 0), int(bot.id or 0)
    finally:
        session.close()


def test_upsert_agent_campaign_persists_single_config_row(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, _ = _seed_agent_and_bot(session_factory)

    row = upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2000-01-01 00:00:00",
        ends_at="2099-12-31 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2000-01-01 00:00:00",
        ends_at="2099-12-31 23:59:59",
        first_deposit_bonus_rate=Decimal("0.06"),
        first_deposit_bonus_amount=Decimal("12.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    session = session_factory()
    try:
        rows = list(
            session.exec(
                select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(agent_id))
            ).all()
        )
    finally:
        session.close()

    assert row["status"] == "active"
    assert len(rows) == 1
    assert Decimal(str(rows[0].first_deposit_bonus_rate)) == Decimal("0.0600")


def test_upsert_agent_campaign_rejects_invalid_time_window(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, _ = _seed_agent_and_bot(session_factory)

    with pytest.raises(ValueError, match="end"):
        upsert_agent_campaign_config(
            agent_id=agent_id,
            actor_username="admin",
            is_enabled=True,
            starts_at="2026-04-30 00:00:00",
            ends_at="2026-04-01 00:00:00",
            first_deposit_bonus_rate=Decimal("0.05"),
            first_deposit_bonus_amount=Decimal("10.00"),
            display_title="首充活动",
            display_subtitle="首次充值即可得奖励",
            session_factory=session_factory,
        )


def test_get_active_campaign_for_bot_formats_display_payload(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, bot_id = _seed_agent_and_bot(session_factory)

    upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2026-04-01 00:00:00",
        ends_at="2026-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    payload = get_active_campaign_for_bot(
        bot_id=bot_id,
        now=datetime(2026, 4, 10, 10, 0, 0),
        session_factory=session_factory,
    )
    assert payload["summary"] == "首次充值赠送 5% + 10 USDT"


def test_upsert_agent_campaign_returns_disabled_status_when_disabled(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, _ = _seed_agent_and_bot(session_factory)

    row = upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=False,
        starts_at="2026-04-01 00:00:00",
        ends_at="2026-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    assert row["status"] == "disabled"


def test_upsert_agent_campaign_returns_upcoming_status_when_start_is_future(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, _ = _seed_agent_and_bot(session_factory)

    row = upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2099-04-01 00:00:00",
        ends_at="2099-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    assert row["status"] == "upcoming"


def test_upsert_agent_campaign_returns_expired_status_when_end_is_past(tmp_path):
    session_factory = _build_session_factory(tmp_path)
    agent_id, _ = _seed_agent_and_bot(session_factory)

    row = upsert_agent_campaign_config(
        agent_id=agent_id,
        actor_username="admin",
        is_enabled=True,
        starts_at="2020-04-01 00:00:00",
        ends_at="2020-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )

    assert row["status"] == "expired"
