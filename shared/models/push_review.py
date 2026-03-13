"""Push review task persistence model."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class PushReviewStatus(str, Enum):
    """Push review task status."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PushReviewTask(SQLModel, table=True):
    """Persistent review record before push campaign creation."""

    __tablename__ = "push_review_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_id: int = Field(default=0, index=True)
    inventory_name: str = Field(default="")
    merchant_name: str = Field(default="")
    inventory_library_id: Optional[int] = Field(
        default=None,
        foreign_key="inventory_libraries.id",
        index=True,
    )
    merchant_id: Optional[int] = Field(
        default=None,
        foreign_key="merchants.id",
        index=True,
    )
    status: PushReviewStatus = Field(default="pending_review", index=True)
    source: str = Field(default="inventory_import")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by: Optional[int] = Field(default=None, foreign_key="admin_users.id", index=True)
    reviewed_by_name: str = Field(default="")
