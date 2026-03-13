"""Audit logs for sensitive admin-side operations."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class AdminAuditLog(SQLModel, table=True):
    """Immutable audit entry for administrative actions."""

    __tablename__ = "admin_audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    operator_id: Optional[int] = Field(
        default=None,
        foreign_key="admin_users.id",
        index=True,
        description="Admin user id",
    )
    action: str = Field(index=True, description="Action name")
    target_type: str = Field(default="", description="Target entity type")
    target_id: Optional[int] = Field(default=None, description="Target entity id")
    request_id: Optional[str] = Field(
        default=None,
        index=True,
        description="Idempotency/request tracing id",
    )
    detail_json: str = Field(default="{}", description="JSON encoded details")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
