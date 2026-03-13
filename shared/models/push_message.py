"""Push message persistence models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class PushScope(str, Enum):
    """Push scope."""

    INVENTORY = "inventory"
    GLOBAL = "global"


class PushStatus(str, Enum):
    """Push lifecycle status."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PushMessageTask(SQLModel, table=True):
    """Push campaign table."""

    __tablename__ = "push_message_tasks"
    __table_args__ = (
        Index("ix_push_message_tasks_status_created_at", "status", "created_at"),
        Index("ix_push_message_tasks_status_scheduled_at", "status", "scheduled_publish_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    dedup_key: str = Field(index=True, unique=True, description="Idempotency key")
    scope: PushScope = Field(default=PushScope.INVENTORY, description="Push scope")
    status: PushStatus = Field(default=PushStatus.PENDING_REVIEW, index=True, description="Task status")

    inventory_ids_json: str = Field(default="[]", description="Inventory ID list JSON")
    inventory_names_json: str = Field(default="[]", description="Inventory name list JSON")
    bot_ids_json: str = Field(default="[]", description="Bot ID list JSON")
    bot_names_json: str = Field(default="[]", description="Bot name list JSON")
    is_global: bool = Field(default=False, description="Global push flag")

    markdown_content: str = Field(default="", description="Markdown content")
    ad_content: str = Field(default="", description="Ad content")
    ad_only_push: bool = Field(default=False, description="Ad-only flag")
    scheduled_publish_at: Optional[datetime] = Field(default=None, description="Scheduled time")
    priority: str = Field(default="normal", description="Priority")
    queue_partition: str = Field(default="primary", description="Queue partition")

    retry_count: int = Field(default=0, description="Retry count")
    max_retries: int = Field(default=3, description="Max retries")
    failover_enabled: bool = Field(default=False, description="Failover enabled")
    failover_channel: str = Field(default="", description="Failover channel")
    last_error: str = Field(default="", description="Last error")

    created_by: str = Field(default="system", description="Created by")
    approved_by: str = Field(default="", description="Approved by")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    approved_at: Optional[datetime] = Field(default=None)
    queued_at: Optional[datetime] = Field(default=None)
    sent_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class PushMessageAuditLog(SQLModel, table=True):
    """Push audit trail table."""

    __tablename__ = "push_message_audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    related_type: str = Field(description="Related type: review/campaign")
    related_id: int = Field(index=True, description="Related record ID")
    action: str = Field(description="Action")
    operator: str = Field(default="system", description="Operator")
    message: str = Field(default="", description="Audit message")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
