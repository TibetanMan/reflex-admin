"""Bot-scoped user account model for balance isolation."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


class BotUserAccount(SQLModel, table=True):
    """Per-user per-bot account for isolated wallet stats."""

    __tablename__ = "bot_user_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "bot_id", name="uq_bot_user_accounts_user_bot"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bot_id: int = Field(foreign_key="bot_instances.id", index=True)

    balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
    )
    total_deposit: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
    )
    total_spent: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
    )
    order_count: int = Field(default=0)
    is_banned: bool = Field(default=False)
    ban_reason: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_active_at: Optional[datetime] = Field(default=None)
