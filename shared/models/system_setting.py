"""System-level key/value settings persisted in database."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class SystemSetting(SQLModel, table=True):
    """Persistent system configuration entry."""

    __tablename__ = "system_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True, description="Setting key")
    value_json: str = Field(default="{}", description="JSON encoded value")
    updated_by: Optional[int] = Field(
        default=None,
        foreign_key="admin_users.id",
        description="Admin user id",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
