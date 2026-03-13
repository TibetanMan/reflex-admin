"""Inventory library and import task models."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .product import ProductItem


class InventoryLibraryStatus(str, Enum):
    """Inventory library status."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class InventoryImportTaskStatus(str, Enum):
    """Inventory import task status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InventoryLibrary(SQLModel, table=True):
    """Library-level inventory model used by inventory page."""

    __tablename__ = "inventory_libraries"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Library name")
    merchant_id: int = Field(foreign_key="merchants.id", index=True)
    category_id: int = Field(foreign_key="categories.id", index=True)
    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    pick_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    status: InventoryLibraryStatus = Field(default="active", index=True)
    is_bot_enabled: bool = Field(default=True, index=True)
    total_count: int = Field(default=0)
    sold_count: int = Field(default=0)
    remaining_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    items: List["ProductItem"] = Relationship(back_populates="inventory_library")
    import_tasks: List["InventoryImportTask"] = Relationship(back_populates="library")


class InventoryImportTask(SQLModel, table=True):
    """Inventory import task and progress tracking."""

    __tablename__ = "inventory_import_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    library_id: int = Field(foreign_key="inventory_libraries.id", index=True)
    operator_id: Optional[int] = Field(default=None, foreign_key="admin_users.id", index=True)
    source_filename: str = Field(description="Uploaded source file name")
    delimiter: str = Field(default="|")
    push_ad_enabled: bool = Field(default=False)
    total: int = Field(default=0)
    success: int = Field(default=0)
    duplicate: int = Field(default=0)
    invalid: int = Field(default=0)
    status: InventoryImportTaskStatus = Field(default="pending", index=True)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    library: Optional["InventoryLibrary"] = Relationship(back_populates="import_tasks")
    line_errors: List["InventoryImportLineError"] = Relationship(back_populates="task")


class InventoryImportLineError(SQLModel, table=True):
    """Optional per-line import failure detail."""

    __tablename__ = "inventory_import_line_errors"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="inventory_import_tasks.id", index=True)
    line_number: int = Field(default=0)
    raw_line: str = Field(default="")
    error_reason: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    task: Optional["InventoryImportTask"] = Relationship(back_populates="line_errors")
