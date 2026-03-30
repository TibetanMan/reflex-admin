"""Agent campaign configuration and reward grant models."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


class AgentCampaignConfig(SQLModel, table=True):
    __tablename__ = "agent_campaign_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", unique=True, index=True)
    is_enabled: bool = Field(default=False)
    starts_at: Optional[datetime] = Field(default=None)
    ends_at: Optional[datetime] = Field(default=None)
    first_deposit_bonus_rate: Decimal = Field(
        sa_column=Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    )
    first_deposit_bonus_amount: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    )
    display_title: Optional[str] = Field(default=None)
    display_subtitle: Optional[str] = Field(default=None)
    updated_by: Optional[int] = Field(default=None, foreign_key="admin_users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class CampaignRewardGrant(SQLModel, table=True):
    __tablename__ = "campaign_reward_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "bot_id", "grant_type", name="uq_campaign_reward_user_bot_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_config_id: Optional[int] = Field(default=None, foreign_key="agent_campaign_configs.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bot_id: int = Field(foreign_key="bot_instances.id", index=True)
    grant_type: str = Field(index=True)
    reward_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    operator_id: Optional[int] = Field(default=None, foreign_key="admin_users.id")
    remark: Optional[str] = Field(default=None)
