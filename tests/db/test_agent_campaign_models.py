from shared.models.agent_campaign import AgentCampaignConfig, CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction


def test_campaign_models_are_registered_in_sqlmodel_metadata():
    assert AgentCampaignConfig.__tablename__ == "agent_campaign_configs"
    assert CampaignRewardGrant.__tablename__ == "campaign_reward_grants"


def test_balance_action_exposes_campaign_bonus():
    assert BalanceAction.CAMPAIGN_BONUS.value == "campaign_bonus"
