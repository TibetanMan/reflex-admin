"""Cart models."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class CartItem(SQLModel, table=True):
    """User cart item row."""

    __tablename__ = "cart_items"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="users.id", index=True, description="User ID")
    bot_id: Optional[int] = Field(default=None, foreign_key="bot_instances.id", index=True, description="Bot ID")

    category_id: int = Field(description="Category ID")
    category_query: str = Field(description="Search query")

    quantity: int = Field(default=1, description="Quantity")

    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False), description="Unit price")
    subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False), description="Subtotal")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at: Optional[datetime] = Field(default=None, description="Expires at")

    user: Optional["User"] = Relationship(back_populates="cart_items")

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expires_at
