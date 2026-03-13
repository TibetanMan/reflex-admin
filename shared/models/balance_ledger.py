"""Traceable user balance changes."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class BalanceAction(str, Enum):
    """Supported balance mutation types."""

    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    MANUAL = "manual"


class BalanceLedger(SQLModel, table=True):
    """Append-only balance ledger table."""

    __tablename__ = "balance_ledgers"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bot_id: Optional[int] = Field(default=None, foreign_key="bot_instances.id", index=True)
    action: BalanceAction = Field(index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    before_balance: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    after_balance: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    operator_id: Optional[int] = Field(default=None, foreign_key="admin_users.id")
    remark: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
