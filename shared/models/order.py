"""Order models."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class OrderStatus(str, Enum):
    """Order status enum."""

    PENDING = "pending"
    PAID = "paid"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Order(SQLModel, table=True):
    """Order header table."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_bot_status_created_at", "bot_id", "status", "created_at"),
        Index("ix_orders_user_created_at", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    order_no: str = Field(unique=True, index=True, description="Order number")

    user_id: int = Field(foreign_key="users.id", index=True, description="User ID")
    bot_id: int = Field(
        foreign_key="bot_instances.id",
        index=True,
        description="Bot ID",
    )

    total_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    paid_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))

    items_count: int = Field(default=0, description="Item count")
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True, description="Order status")

    platform_profit: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))
    agent_profit: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))
    supplier_profit: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))

    remark: Optional[str] = Field(default=None, description="Remark")
    refund_reason: Optional[str] = Field(default=None, description="Refund reason")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    paid_at: Optional[datetime] = Field(default=None, description="Paid at")
    completed_at: Optional[datetime] = Field(default=None, description="Completed at")
    refunded_at: Optional[datetime] = Field(default=None, description="Refunded at")

    user: Optional["User"] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")

    @property
    def is_paid(self) -> bool:
        return self.status in [OrderStatus.PAID, OrderStatus.COMPLETED]

    @property
    def can_refund(self) -> bool:
        return self.status in [OrderStatus.PAID, OrderStatus.COMPLETED]


class OrderItem(SQLModel, table=True):
    """Order item snapshot table."""

    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True, description="Order ID")
    product_id: int = Field(description="Product ID")

    product_data: str = Field(description="Product snapshot data")
    category_name: str = Field(description="Category name")
    bin_number: str = Field(description="BIN")
    country_code: str = Field(description="Country code")

    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    quantity: int = Field(default=1, description="Quantity")
    subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    purchase_mode: Optional[str] = Field(default=None, description="Purchase mode: head/random/prefix")
    purchase_filter_json: Optional[str] = Field(default=None, description="Purchase filter snapshot JSON")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    order: Optional["Order"] = Relationship(back_populates="items")
