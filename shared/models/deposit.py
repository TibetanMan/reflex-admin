"""Deposit models."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class DepositStatus(str, Enum):
    """Deposit status enum."""

    PENDING = "pending"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DepositMethod(str, Enum):
    """Deposit method enum."""

    USDT_TRC20 = "usdt_trc20"
    USDT_ERC20 = "usdt_erc20"
    MANUAL = "manual"


class Deposit(SQLModel, table=True):
    """Deposit table."""

    __tablename__ = "deposits"
    __table_args__ = (
        Index("ix_deposits_status_created_at", "status", "created_at"),
        Index("ix_deposits_bot_status_created_at", "bot_id", "status", "created_at"),
        Index("ix_deposits_user_created_at", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    deposit_no: str = Field(unique=True, index=True, description="Deposit number")

    user_id: int = Field(foreign_key="users.id", index=True, description="User ID")
    bot_id: int = Field(foreign_key="bot_instances.id", index=True, description="Bot ID")

    amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    actual_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))

    method: DepositMethod = Field(default=DepositMethod.USDT_TRC20, description="Deposit method")

    to_address: str = Field(description="Target address")
    from_address: Optional[str] = Field(default=None, description="Source address")
    tx_hash: Optional[str] = Field(default=None, unique=True, description="Transaction hash")
    block_number: Optional[int] = Field(default=None, description="Block number")
    confirmations: int = Field(default=0, description="Confirmations")

    status: DepositStatus = Field(default=DepositStatus.PENDING, index=True, description="Deposit status")

    operator_id: Optional[int] = Field(default=None, foreign_key="admin_users.id", description="Operator ID")
    operator_remark: Optional[str] = Field(default=None, description="Operator remark")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at: Optional[datetime] = Field(default=None, description="Completed at")
    expires_at: Optional[datetime] = Field(default=None, description="Expires at")

    user: Optional["User"] = Relationship(back_populates="deposits")

    @property
    def is_completed(self) -> bool:
        return self.status == DepositStatus.COMPLETED

    @property
    def is_pending(self) -> bool:
        return self.status in [DepositStatus.PENDING, DepositStatus.CONFIRMING]
