"""Wallet address model."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class WalletStatus(str, Enum):
    """Wallet status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FULL = "full"


class WalletAddress(SQLModel, table=True):
    """Wallet address table for on-chain monitoring."""

    __tablename__ = "wallet_addresses"

    id: Optional[int] = Field(default=None, primary_key=True)

    address: str = Field(unique=True, index=True, description="Wallet address")
    private_key: Optional[str] = Field(default=None, description="Encrypted private key")

    bot_id: Optional[int] = Field(default=None, foreign_key="bot_instances.id", index=True, description="Bot ID")
    agent_id: Optional[int] = Field(default=None, foreign_key="agents.id", index=True, description="Agent ID")
    is_platform: bool = Field(default=False, description="Platform wallet flag")

    balance: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))
    total_received: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))

    status: WalletStatus = Field(default=WalletStatus.ACTIVE, index=True, description="Wallet status")
    last_checked_at: Optional[datetime] = Field(default=None, description="Last checked at")
    last_tx_at: Optional[datetime] = Field(default=None, description="Last transaction at")

    label: Optional[str] = Field(default=None, description="Label")
    remark: Optional[str] = Field(default=None, description="Remark")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @property
    def is_active(self) -> bool:
        return self.status == WalletStatus.ACTIVE

    @property
    def masked_address(self) -> str:
        if len(self.address) > 20:
            return f"{self.address[:8]}...{self.address[-6:]}"
        return self.address
