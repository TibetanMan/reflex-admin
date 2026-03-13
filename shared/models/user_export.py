"""User source binding and export task models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ExportTaskType(str, Enum):
    """Export task data type."""

    ORDER = "order"
    USER = "user"


class ExportTaskStatus(str, Enum):
    """Export task execution status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserBotSource(SQLModel, table=True):
    """User to bot source mapping for multi-bot attribution."""

    __tablename__ = "user_bot_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "bot_id", name="uq_user_bot_sources_user_bot"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bot_id: int = Field(foreign_key="bot_instances.id", index=True)
    is_primary: bool = Field(default=False)
    bound_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ExportTask(SQLModel, table=True):
    """Unified async export task model for orders and users."""

    __tablename__ = "export_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    type: ExportTaskType = Field(default="order", index=True)
    operator_id: Optional[int] = Field(default=None, foreign_key="admin_users.id", index=True)
    filters_json: str = Field(default="{}")
    status: ExportTaskStatus = Field(default="pending", index=True)
    progress: int = Field(default=0)
    total_records: int = Field(default=0)
    processed_records: int = Field(default=0)
    file_path: Optional[str] = Field(default=None)
    file_name: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    finished_at: Optional[datetime] = Field(default=None)
