"""Product and row-level inventory models."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .category import Category
    from .inventory import InventoryLibrary
    from .merchant import Merchant


class ProductStatus(str, Enum):
    """Product status enum."""

    AVAILABLE = "available"
    SOLD = "sold"
    LOCKED = "locked"
    DEAD = "dead"
    REFUNDED = "refunded"


class ProductItem(SQLModel, table=True):
    """One sellable row item."""

    __tablename__ = "product_items"
    __table_args__ = (
        Index("ix_product_items_status_category_supplier_created", "status", "category_id", "supplier_id", "created_at"),
        Index("ix_product_items_library_status_bin", "inventory_library_id", "status", "bin_number"),
        Index("ix_product_items_library_status_created", "inventory_library_id", "status", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    raw_data: str = Field(description="Raw product data")
    data_hash: str = Field(unique=True, index=True, description="Dedup hash")

    bin_number: str = Field(index=True, description="Card BIN")

    category_id: int = Field(foreign_key="categories.id", index=True, description="Category ID")
    country_code: str = Field(index=True, description="Country code")

    supplier_id: Optional[int] = Field(
        default=None,
        foreign_key="merchants.id",
        index=True,
        description="Merchant ID",
    )
    inventory_library_id: Optional[int] = Field(
        default=None,
        foreign_key="inventory_libraries.id",
        index=True,
        description="Inventory library ID",
    )

    cost_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")))
    selling_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))

    status: ProductStatus = Field(default=ProductStatus.AVAILABLE, index=True, description="Status")

    sold_to_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True, description="Buyer user ID")
    sold_to_bot_id: Optional[int] = Field(default=None, foreign_key="bot_instances.id", index=True, description="Buyer bot ID")
    sold_at: Optional[datetime] = Field(default=None, description="Sold time")
    sold_price: Optional[Decimal] = Field(sa_column=Column(Numeric(18, 2), nullable=True))

    locked_by_user_id: Optional[int] = Field(default=None)
    locked_at: Optional[datetime] = Field(default=None)
    lock_expires_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    category: Optional["Category"] = Relationship(back_populates="products")
    supplier: Optional["Merchant"] = Relationship(back_populates="products")
    inventory_library: Optional["InventoryLibrary"] = Relationship(back_populates="items")

    @property
    def is_available(self) -> bool:
        return self.status == ProductStatus.AVAILABLE

    @property
    def is_sold(self) -> bool:
        return self.status == ProductStatus.SOLD

    @property
    def masked_data(self) -> str:
        if len(self.raw_data) > 20:
            return f"{self.raw_data[:8]}****{self.raw_data[-4:]}"
        return "****"
