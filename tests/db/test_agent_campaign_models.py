from sqlalchemy import inspect
from sqlmodel import SQLModel, create_engine

import shared.models as models
from shared.models.agent_campaign import AgentCampaignConfig, CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction
from shared.schema_patch import apply_runtime_schema_patches


def test_campaign_models_are_exported_from_shared_models():
    assert "AgentCampaignConfig" in models.__all__
    assert "CampaignRewardGrant" in models.__all__
    assert models.AgentCampaignConfig is AgentCampaignConfig
    assert models.CampaignRewardGrant is CampaignRewardGrant


def test_campaign_tables_are_created_with_expected_columns():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)

    assert "agent_campaign_configs" in inspector.get_table_names()
    assert "campaign_reward_grants" in inspector.get_table_names()

    config_columns = {column["name"] for column in inspector.get_columns("agent_campaign_configs")}
    grant_columns = {column["name"] for column in inspector.get_columns("campaign_reward_grants")}

    assert {"created_at", "updated_at"}.issubset(config_columns)
    assert "grant_type" in grant_columns


def test_balance_action_exposes_campaign_bonus():
    assert BalanceAction.CAMPAIGN_BONUS.value == "campaign_bonus"


def test_runtime_schema_patch_executes_campaign_bonus_enum_sql(monkeypatch):
    class _FakeDialect:
        name = "postgresql"

    class _FakeBind:
        dialect = _FakeDialect()

    class _FakeSession:
        def __init__(self):
            self.bind = _FakeBind()
            self.executed = []

        def exec(self, statement):
            self.executed.append(str(statement))

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    fake_session = _FakeSession()
    monkeypatch.setattr("shared.schema_patch.get_db_session", lambda: fake_session)

    apply_runtime_schema_patches()

    assert any(
        "ALTER TYPE balanceaction ADD VALUE IF NOT EXISTS 'campaign_bonus'" in statement
        for statement in fake_session.executed
    )
    assert not any("uq_agent_campaign_configs_agent_id_idx" in statement for statement in fake_session.executed)
    assert not any("uq_campaign_reward_user_bot_type_idx" in statement for statement in fake_session.executed)


def test_runtime_schema_patch_executes_sqlite_campaign_schema_sql(monkeypatch):
    class _FakeDialect:
        name = "sqlite"

    class _FakeBind:
        dialect = _FakeDialect()

    class _FakeSession:
        def __init__(self):
            self.bind = _FakeBind()
            self.executed = []

        def exec(self, statement):
            self.executed.append(str(statement))

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    fake_session = _FakeSession()
    monkeypatch.setattr("shared.schema_patch.get_db_session", lambda: fake_session)

    apply_runtime_schema_patches()

    assert any("CREATE TABLE IF NOT EXISTS agent_campaign_configs" in statement for statement in fake_session.executed)
    assert any("CREATE TABLE IF NOT EXISTS campaign_reward_grants" in statement for statement in fake_session.executed)
    assert not any("ALTER TYPE balanceaction" in statement for statement in fake_session.executed)
    assert not any("uq_agent_campaign_configs_agent_id_idx" in statement for statement in fake_session.executed)
    assert not any("uq_campaign_reward_user_bot_type_idx" in statement for statement in fake_session.executed)
