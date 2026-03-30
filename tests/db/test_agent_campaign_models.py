from shared.models.agent_campaign import AgentCampaignConfig, CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction
from shared.schema_patch import apply_runtime_schema_patches


def test_campaign_models_are_registered_in_sqlmodel_metadata():
    assert AgentCampaignConfig.__tablename__ == "agent_campaign_configs"
    assert CampaignRewardGrant.__tablename__ == "campaign_reward_grants"


def test_balance_action_exposes_campaign_bonus():
    assert BalanceAction.CAMPAIGN_BONUS.value == "campaign_bonus"


def test_agent_campaign_config_exposes_timestamps():
    fields = AgentCampaignConfig.model_fields
    assert "created_at" in fields
    assert "updated_at" in fields


def test_runtime_schema_patch_contains_campaign_timestamp_columns():
    patch_consts = apply_runtime_schema_patches.__code__.co_consts
    patch_sql = " ".join([value for value in patch_consts if isinstance(value, str)])
    assert (
        "CREATE TABLE IF NOT EXISTS agent_campaign_configs ("
        "id SERIAL PRIMARY KEY,"
        "agent_id INTEGER NOT NULL UNIQUE REFERENCES agents(id),"
        "is_enabled BOOLEAN NOT NULL DEFAULT FALSE,"
        "starts_at TIMESTAMP NULL,"
        "ends_at TIMESTAMP NULL,"
        "first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000,"
        "first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
        "display_title TEXT NULL,"
        "display_subtitle TEXT NULL,"
        "updated_by INTEGER NULL REFERENCES admin_users(id),"
        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ")"
    ) in patch_sql
    assert (
        "CREATE TABLE IF NOT EXISTS agent_campaign_configs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "agent_id INTEGER NOT NULL,"
        "is_enabled BOOLEAN NOT NULL DEFAULT 0,"
        "starts_at DATETIME NULL,"
        "ends_at DATETIME NULL,"
        "first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000,"
        "first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
        "display_title TEXT NULL,"
        "display_subtitle TEXT NULL,"
        "updated_by INTEGER NULL,"
        "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "UNIQUE(agent_id)"
        ")"
    ) in patch_sql
