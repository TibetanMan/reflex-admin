"""Message push queue repository abstractions.

This module provides both in-memory and SQLModel-backed adapters.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from threading import RLock
from typing import Any, Callable, Optional, Protocol

from sqlalchemy import delete
from sqlmodel import Session, select

from shared.models.push_message import PushMessageAuditLog, PushMessageTask, PushScope, PushStatus
from shared.models.push_review import PushReviewStatus, PushReviewTask


ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ACTIVE_REVIEW_STATUSES = {"pending_review", "approved"}
ACTIVE_CAMPAIGN_STATUSES = {"queued", "processing", "sent"}


def _now_text() -> str:
    return datetime.now().strftime(ISO_DATETIME_FORMAT)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime(ISO_DATETIME_FORMAT)
    return str(value)


def _parse_optional_datetime(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _is_schedule_due(schedule_text: str) -> bool:
    text = str(schedule_text or "").strip()
    if not text:
        return True
    try:
        scheduled_at = datetime.fromisoformat(text)
    except ValueError:
        return True
    now = datetime.now(tz=scheduled_at.tzinfo) if scheduled_at.tzinfo else datetime.now()
    return scheduled_at <= now


def _json_dumps(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _json_load_list(value: str) -> list[Any]:
    text = str(value or "[]")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _json_load_int_list(value: str) -> list[int]:
    rows: list[int] = []
    for item in _json_load_list(value):
        try:
            rows.append(int(item))
        except (TypeError, ValueError):
            continue
    return rows


def _json_load_str_list(value: str) -> list[str]:
    return [str(item) for item in _json_load_list(value)]


@dataclass
class ReviewTaskRecord:
    id: int
    inventory_id: int
    inventory_name: str
    merchant_name: str
    source: str
    status: str
    created_at: str
    reviewed_at: str = ""
    reviewed_by: str = ""


@dataclass
class PushCampaignRecord:
    id: int
    dedup_key: str
    scope: str
    inventory_ids: list[int]
    inventory_names: list[str]
    bot_ids: list[int]
    bot_names: list[str]
    is_global: bool
    markdown_content: str
    ad_content: str
    ad_only_push: bool
    scheduled_publish_at: str
    priority: str
    queue_partition: str
    status: str
    retry_count: int
    max_retries: int
    failover_enabled: bool
    failover_channel: str
    created_by: str
    approved_by: str
    created_at: str
    approved_at: str
    queued_at: str
    sent_at: str = ""
    last_error: str = ""


@dataclass
class PushAuditRecord:
    id: int
    related_type: str
    related_id: int
    action: str
    operator: str
    message: str
    created_at: str


class PushQueueRepository(Protocol):
    """Repository contract for push queue persistence."""

    def reset(self) -> None: ...

    def register_review_task(
        self, inventory_id: int, inventory_name: str, merchant_name: str, source: str
    ) -> dict[str, Any]: ...

    def approve_review_task(self, review_id: int, reviewed_by: str) -> Optional[dict[str, Any]]: ...

    def list_review_tasks(self) -> list[dict[str, Any]]: ...

    def enqueue_campaign(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def cancel_campaign(self, campaign_id: int, cancelled_by: str) -> Optional[dict[str, Any]]: ...

    def process_queue(self, batch_size: int) -> dict[str, int]: ...

    def list_campaigns(self) -> list[dict[str, Any]]: ...

    def list_audit_logs(self) -> list[dict[str, Any]]: ...


class InMemoryPushQueueRepository:
    """In-memory adapter for local development and tests."""

    def __init__(self):
        self._lock = RLock()
        self._review_seq = 1
        self._campaign_seq = 1
        self._audit_seq = 1
        self._reviews: list[ReviewTaskRecord] = []
        self._campaigns: list[PushCampaignRecord] = []
        self._audits: list[PushAuditRecord] = []

    def reset(self) -> None:
        with self._lock:
            self._review_seq = 1
            self._campaign_seq = 1
            self._audit_seq = 1
            self._reviews = []
            self._campaigns = []
            self._audits = []

    def _write_audit(
        self,
        *,
        related_type: str,
        related_id: int,
        action: str,
        operator: str,
        message: str,
    ) -> None:
        row = PushAuditRecord(
            id=self._audit_seq,
            related_type=related_type,
            related_id=related_id,
            action=action,
            operator=operator,
            message=message,
            created_at=_now_text(),
        )
        self._audit_seq += 1
        self._audits.append(row)

    def register_review_task(
        self,
        inventory_id: int,
        inventory_name: str,
        merchant_name: str,
        source: str = "inventory_import",
    ) -> dict[str, Any]:
        with self._lock:
            for row in self._reviews:
                if row.inventory_id == inventory_id and row.status in ACTIVE_REVIEW_STATUSES:
                    return asdict(row)

            record = ReviewTaskRecord(
                id=self._review_seq,
                inventory_id=inventory_id,
                inventory_name=inventory_name.strip() or f"Inventory-{inventory_id}",
                merchant_name=merchant_name.strip() or "-",
                source=source,
                status="pending_review",
                created_at=_now_text(),
            )
            self._review_seq += 1
            self._reviews.append(record)
            self._write_audit(
                related_type="review",
                related_id=record.id,
                action="created",
                operator="system",
                message=f"review task created for inventory {record.inventory_id}",
            )
            return asdict(record)

    def approve_review_task(self, review_id: int, reviewed_by: str) -> Optional[dict[str, Any]]:
        with self._lock:
            for row in self._reviews:
                if row.id != int(review_id):
                    continue
                row.status = "approved"
                row.reviewed_at = _now_text()
                row.reviewed_by = reviewed_by
                self._write_audit(
                    related_type="review",
                    related_id=row.id,
                    action="approved",
                    operator=reviewed_by,
                    message=f"review task {row.id} approved",
                )
                return asdict(row)
            return None

    def list_review_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            ordered = sorted(
                self._reviews,
                key=lambda item: (item.status != "pending_review", item.id),
            )
            return [asdict(row) for row in ordered]

    def _compute_dedup_key(self, payload: dict[str, Any]) -> str:
        scope = str(payload.get("scope") or "inventory")
        inventory_ids = ",".join(str(v) for v in sorted(payload.get("inventory_ids", [])))
        bot_ids = ",".join(str(v) for v in sorted(payload.get("bot_ids", [])))
        is_global = "1" if payload.get("is_global") else "0"
        ad_only = "1" if payload.get("ad_only_push") else "0"
        scheduled_publish_at = str(payload.get("scheduled_publish_at") or "")
        content_raw = f"{payload.get('markdown_content', '')}\n||\n{payload.get('ad_content', '')}"
        content_hash = sha256(content_raw.encode("utf-8")).hexdigest()
        base = (
            f"{scope}|{inventory_ids}|{bot_ids}|{is_global}|{ad_only}|"
            f"{scheduled_publish_at}|{content_hash}"
        )
        return sha256(base.encode("utf-8")).hexdigest()

    def enqueue_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            dedup_key = self._compute_dedup_key(payload)
            for row in self._campaigns:
                if row.dedup_key == dedup_key and row.status in ACTIVE_CAMPAIGN_STATUSES:
                    return asdict(row)

            created_by = str(payload.get("created_by") or "system")
            approved_by = str(payload.get("approved_by") or created_by)
            now = _now_text()
            record = PushCampaignRecord(
                id=self._campaign_seq,
                dedup_key=dedup_key,
                scope=str(payload.get("scope") or "inventory"),
                inventory_ids=[int(v) for v in payload.get("inventory_ids", [])],
                inventory_names=[str(v) for v in payload.get("inventory_names", [])],
                bot_ids=[int(v) for v in payload.get("bot_ids", [])],
                bot_names=[str(v) for v in payload.get("bot_names", [])],
                is_global=bool(payload.get("is_global", False)),
                markdown_content=str(payload.get("markdown_content") or ""),
                ad_content=str(payload.get("ad_content") or ""),
                ad_only_push=bool(payload.get("ad_only_push", False)),
                scheduled_publish_at=str(payload.get("scheduled_publish_at") or ""),
                priority=str(payload.get("priority") or "normal"),
                queue_partition=str(payload.get("queue_partition") or "primary"),
                status="queued",
                retry_count=0,
                max_retries=max(0, int(payload.get("max_retries", 3))),
                failover_enabled=bool(payload.get("failover_enabled", False)),
                failover_channel=str(payload.get("failover_channel") or ""),
                created_by=created_by,
                approved_by=approved_by,
                created_at=now,
                approved_at=now,
                queued_at=now,
            )
            self._campaign_seq += 1
            self._campaigns.append(record)
            self._write_audit(
                related_type="campaign",
                related_id=record.id,
                action="queued",
                operator=created_by,
                message=f"campaign {record.id} queued",
            )
            return asdict(record)

    def cancel_campaign(self, campaign_id: int, cancelled_by: str) -> Optional[dict[str, Any]]:
        with self._lock:
            for row in self._campaigns:
                if row.id != int(campaign_id):
                    continue
                if row.status == "cancelled":
                    return asdict(row)
                if row.status in {"sent", "failed"}:
                    return asdict(row)
                row.status = "cancelled"
                row.last_error = "cancelled by operator"
                self._write_audit(
                    related_type="campaign",
                    related_id=row.id,
                    action="cancelled",
                    operator=str(cancelled_by or "system"),
                    message=f"campaign {row.id} cancelled",
                )
                return asdict(row)
            return None

    def _mark_retry_or_failed(self, row: PushCampaignRecord) -> str:
        row.retry_count += 1
        if row.retry_count > row.max_retries:
            row.status = "failed"
            row.last_error = "max retries exceeded"
            return "failed"
        row.status = "queued"
        if row.failover_enabled and row.failover_channel:
            row.queue_partition = row.failover_channel
        return "retried"

    def process_queue(self, batch_size: int = 20) -> dict[str, int]:
        with self._lock:
            queued = [
                row
                for row in self._campaigns
                if row.status == "queued" and _is_schedule_due(row.scheduled_publish_at)
            ]
            queued = queued[: max(1, batch_size)]
            processed = 0
            sent = 0
            failed = 0
            retried = 0

            for row in queued:
                processed += 1
                row.status = "processing"

                simulate_failure = "#force-fail" in row.markdown_content
                if not simulate_failure:
                    row.status = "sent"
                    row.sent_at = _now_text()
                    sent += 1
                    self._write_audit(
                        related_type="campaign",
                        related_id=row.id,
                        action="sent",
                        operator="queue_worker",
                        message=f"campaign {row.id} sent",
                    )
                    continue

                result = self._mark_retry_or_failed(row)
                if result == "failed":
                    failed += 1
                    self._write_audit(
                        related_type="campaign",
                        related_id=row.id,
                        action="failed",
                        operator="queue_worker",
                        message=f"campaign {row.id} failed after retries",
                    )
                else:
                    retried += 1
                    self._write_audit(
                        related_type="campaign",
                        related_id=row.id,
                        action="retried",
                        operator="queue_worker",
                        message=f"campaign {row.id} retried",
                    )

            return {
                "processed": processed,
                "sent": sent,
                "failed": failed,
                "retried": retried,
            }

    def list_campaigns(self) -> list[dict[str, Any]]:
        with self._lock:
            ordered = sorted(self._campaigns, key=lambda item: item.id, reverse=True)
            return [asdict(row) for row in ordered]

    def list_audit_logs(self) -> list[dict[str, Any]]:
        with self._lock:
            ordered = sorted(self._audits, key=lambda item: item.id, reverse=True)
            return [asdict(row) for row in ordered]


class SqlModelPushQueueRepository:
    """SQLModel-backed adapter for persistent queue storage."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        if session_factory is None:
            from shared.database import get_db_session

            self._session_factory = get_db_session
        else:
            self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def _write_audit(
        self,
        session: Session,
        *,
        related_type: str,
        related_id: int,
        action: str,
        operator: str,
        message: str,
    ) -> None:
        session.add(
            PushMessageAuditLog(
                related_type=related_type,
                related_id=related_id,
                action=action,
                operator=operator,
                message=message,
            )
        )

    def _review_to_dict(self, row: PushReviewTask) -> dict[str, Any]:
        reviewed_by_text = row.reviewed_by_name or (str(row.reviewed_by) if row.reviewed_by else "")
        inventory_id = int(row.inventory_id or row.inventory_library_id or 0)
        return {
            "id": int(row.id or 0),
            "inventory_id": inventory_id,
            "inventory_name": row.inventory_name or f"Inventory-{inventory_id}",
            "merchant_name": row.merchant_name or "-",
            "source": str(row.source or "inventory_import"),
            "status": str(row.status.value if hasattr(row.status, "value") else row.status),
            "created_at": _to_text(row.created_at),
            "reviewed_at": _to_text(row.reviewed_at),
            "reviewed_by": reviewed_by_text,
        }

    def _campaign_to_dict(self, row: PushMessageTask) -> dict[str, Any]:
        return {
            "id": int(row.id or 0),
            "dedup_key": str(row.dedup_key),
            "scope": str(row.scope.value if hasattr(row.scope, "value") else row.scope),
            "inventory_ids": _json_load_int_list(row.inventory_ids_json),
            "inventory_names": _json_load_str_list(row.inventory_names_json),
            "bot_ids": _json_load_int_list(row.bot_ids_json),
            "bot_names": _json_load_str_list(row.bot_names_json),
            "is_global": bool(row.is_global),
            "markdown_content": str(row.markdown_content or ""),
            "ad_content": str(row.ad_content or ""),
            "ad_only_push": bool(row.ad_only_push),
            "scheduled_publish_at": _to_text(row.scheduled_publish_at),
            "priority": str(row.priority or "normal"),
            "queue_partition": str(row.queue_partition or "primary"),
            "status": str(row.status.value if hasattr(row.status, "value") else row.status),
            "retry_count": int(row.retry_count or 0),
            "max_retries": int(row.max_retries or 0),
            "failover_enabled": bool(row.failover_enabled),
            "failover_channel": str(row.failover_channel or ""),
            "created_by": str(row.created_by or "system"),
            "approved_by": str(row.approved_by or ""),
            "created_at": _to_text(row.created_at),
            "approved_at": _to_text(row.approved_at),
            "queued_at": _to_text(row.queued_at),
            "sent_at": _to_text(row.sent_at),
            "last_error": str(row.last_error or ""),
        }

    def _audit_to_dict(self, row: PushMessageAuditLog) -> dict[str, Any]:
        return {
            "id": int(row.id or 0),
            "related_type": str(row.related_type),
            "related_id": int(row.related_id),
            "action": str(row.action),
            "operator": str(row.operator),
            "message": str(row.message or ""),
            "created_at": _to_text(row.created_at),
        }

    def reset(self) -> None:
        session = self._session()
        try:
            session.exec(delete(PushMessageAuditLog))
            session.exec(delete(PushMessageTask))
            session.exec(delete(PushReviewTask))
            session.commit()
        finally:
            session.close()

    def register_review_task(
        self,
        inventory_id: int,
        inventory_name: str,
        merchant_name: str,
        source: str = "inventory_import",
    ) -> dict[str, Any]:
        session = self._session()
        try:
            row = session.exec(
                select(PushReviewTask)
                .where(
                    PushReviewTask.inventory_id == int(inventory_id),
                    PushReviewTask.status.in_([PushReviewStatus.PENDING_REVIEW, PushReviewStatus.APPROVED]),
                )
                .order_by(PushReviewTask.id.desc())
            ).first()
            if row:
                return self._review_to_dict(row)

            record = PushReviewTask(
                inventory_id=int(inventory_id),
                inventory_name=inventory_name.strip() or f"Inventory-{inventory_id}",
                merchant_name=merchant_name.strip() or "-",
                source=source,
                status=PushReviewStatus.PENDING_REVIEW,
            )
            session.add(record)
            session.flush()
            self._write_audit(
                session,
                related_type="review",
                related_id=int(record.id or 0),
                action="created",
                operator="system",
                message=f"review task created for inventory {inventory_id}",
            )
            session.commit()
            session.refresh(record)
            return self._review_to_dict(record)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def approve_review_task(self, review_id: int, reviewed_by: str) -> Optional[dict[str, Any]]:
        session = self._session()
        try:
            row = session.get(PushReviewTask, int(review_id))
            if not row:
                return None
            row.status = PushReviewStatus.APPROVED
            row.reviewed_at = datetime.now()
            row.reviewed_by_name = str(reviewed_by)
            if str(reviewed_by).isdigit():
                row.reviewed_by = int(reviewed_by)
            self._write_audit(
                session,
                related_type="review",
                related_id=int(row.id or 0),
                action="approved",
                operator=str(reviewed_by),
                message=f"review task {review_id} approved",
            )
            session.commit()
            session.refresh(row)
            return self._review_to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_review_tasks(self) -> list[dict[str, Any]]:
        session = self._session()
        try:
            rows = list(session.exec(select(PushReviewTask)).all())
            mapped = [self._review_to_dict(item) for item in rows]
            return sorted(mapped, key=lambda item: (item["status"] != "pending_review", item["id"]))
        finally:
            session.close()

    def _compute_dedup_key(self, payload: dict[str, Any]) -> str:
        scope = str(payload.get("scope") or "inventory")
        inventory_ids = ",".join(str(v) for v in sorted(payload.get("inventory_ids", [])))
        bot_ids = ",".join(str(v) for v in sorted(payload.get("bot_ids", [])))
        is_global = "1" if payload.get("is_global") else "0"
        ad_only = "1" if payload.get("ad_only_push") else "0"
        scheduled_publish_at = str(payload.get("scheduled_publish_at") or "")
        content_raw = f"{payload.get('markdown_content', '')}\n||\n{payload.get('ad_content', '')}"
        content_hash = sha256(content_raw.encode("utf-8")).hexdigest()
        base = (
            f"{scope}|{inventory_ids}|{bot_ids}|{is_global}|{ad_only}|"
            f"{scheduled_publish_at}|{content_hash}"
        )
        return sha256(base.encode("utf-8")).hexdigest()

    def enqueue_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._session()
        try:
            dedup_key = self._compute_dedup_key(payload)
            existing = session.exec(
                select(PushMessageTask)
                .where(
                    PushMessageTask.dedup_key == dedup_key,
                    PushMessageTask.status.in_([PushStatus.QUEUED, PushStatus.PROCESSING, PushStatus.SENT]),
                )
                .order_by(PushMessageTask.id.desc())
            ).first()
            if existing:
                return self._campaign_to_dict(existing)

            scope_raw = str(payload.get("scope") or "inventory")
            scope = PushScope.GLOBAL if scope_raw == PushScope.GLOBAL.value else PushScope.INVENTORY
            created_by = str(payload.get("created_by") or "system")
            approved_by = str(payload.get("approved_by") or created_by)
            now = datetime.now()

            row = PushMessageTask(
                dedup_key=dedup_key,
                scope=scope,
                status=PushStatus.QUEUED,
                inventory_ids_json=_json_dumps([int(v) for v in payload.get("inventory_ids", [])]),
                inventory_names_json=_json_dumps([str(v) for v in payload.get("inventory_names", [])]),
                bot_ids_json=_json_dumps([int(v) for v in payload.get("bot_ids", [])]),
                bot_names_json=_json_dumps([str(v) for v in payload.get("bot_names", [])]),
                is_global=bool(payload.get("is_global", False)),
                markdown_content=str(payload.get("markdown_content") or ""),
                ad_content=str(payload.get("ad_content") or ""),
                ad_only_push=bool(payload.get("ad_only_push", False)),
                scheduled_publish_at=_parse_optional_datetime(str(payload.get("scheduled_publish_at") or "")),
                priority=str(payload.get("priority") or "normal"),
                queue_partition=str(payload.get("queue_partition") or "primary"),
                retry_count=0,
                max_retries=max(0, int(payload.get("max_retries", 3))),
                failover_enabled=bool(payload.get("failover_enabled", False)),
                failover_channel=str(payload.get("failover_channel") or ""),
                created_by=created_by,
                approved_by=approved_by,
                created_at=now,
                approved_at=now,
                queued_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            self._write_audit(
                session,
                related_type="campaign",
                related_id=int(row.id or 0),
                action="queued",
                operator=created_by,
                message=f"campaign {row.id} queued",
            )
            session.commit()
            session.refresh(row)
            return self._campaign_to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def cancel_campaign(self, campaign_id: int, cancelled_by: str) -> Optional[dict[str, Any]]:
        session = self._session()
        try:
            row = session.get(PushMessageTask, int(campaign_id))
            if row is None:
                return None
            if row.status == PushStatus.CANCELLED:
                return self._campaign_to_dict(row)
            if row.status in {PushStatus.SENT, PushStatus.FAILED}:
                return self._campaign_to_dict(row)

            row.status = PushStatus.CANCELLED
            row.last_error = "cancelled by operator"
            row.updated_at = datetime.now()
            session.add(row)
            self._write_audit(
                session,
                related_type="campaign",
                related_id=int(row.id or 0),
                action="cancelled",
                operator=str(cancelled_by or "system"),
                message=f"campaign {row.id} cancelled",
            )
            session.commit()
            session.refresh(row)
            return self._campaign_to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mark_retry_or_failed(self, row: PushMessageTask) -> str:
        row.retry_count += 1
        if row.retry_count > row.max_retries:
            row.status = PushStatus.FAILED
            row.last_error = "max retries exceeded"
            row.updated_at = datetime.now()
            return "failed"
        row.status = PushStatus.QUEUED
        if row.failover_enabled and row.failover_channel:
            row.queue_partition = row.failover_channel
        row.updated_at = datetime.now()
        return "retried"

    def process_queue(self, batch_size: int = 20) -> dict[str, int]:
        session = self._session()
        try:
            rows = list(
                session.exec(
                    select(PushMessageTask)
                    .where(PushMessageTask.status == PushStatus.QUEUED)
                    .order_by(PushMessageTask.id.asc())
                ).all()
            )
            due_rows = [
                row
                for row in rows
                if _is_schedule_due(_to_text(row.scheduled_publish_at))
            ][: max(1, batch_size)]

            processed = 0
            sent = 0
            failed = 0
            retried = 0

            for row in due_rows:
                processed += 1
                row.status = PushStatus.PROCESSING
                row.updated_at = datetime.now()

                simulate_failure = "#force-fail" in str(row.markdown_content or "")
                if not simulate_failure:
                    row.status = PushStatus.SENT
                    row.sent_at = datetime.now()
                    row.updated_at = datetime.now()
                    sent += 1
                    self._write_audit(
                        session,
                        related_type="campaign",
                        related_id=int(row.id or 0),
                        action="sent",
                        operator="queue_worker",
                        message=f"campaign {row.id} sent",
                    )
                    continue

                result = self._mark_retry_or_failed(row)
                if result == "failed":
                    failed += 1
                    self._write_audit(
                        session,
                        related_type="campaign",
                        related_id=int(row.id or 0),
                        action="failed",
                        operator="queue_worker",
                        message=f"campaign {row.id} failed after retries",
                    )
                else:
                    retried += 1
                    self._write_audit(
                        session,
                        related_type="campaign",
                        related_id=int(row.id or 0),
                        action="retried",
                        operator="queue_worker",
                        message=f"campaign {row.id} retried",
                    )

            session.commit()
            return {
                "processed": processed,
                "sent": sent,
                "failed": failed,
                "retried": retried,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_campaigns(self) -> list[dict[str, Any]]:
        session = self._session()
        try:
            rows = list(session.exec(select(PushMessageTask).order_by(PushMessageTask.id.desc())).all())
            return [self._campaign_to_dict(row) for row in rows]
        finally:
            session.close()

    def list_audit_logs(self) -> list[dict[str, Any]]:
        session = self._session()
        try:
            rows = list(
                session.exec(
                    select(PushMessageAuditLog).order_by(PushMessageAuditLog.id.desc())
                ).all()
            )
            return [self._audit_to_dict(row) for row in rows]
        finally:
            session.close()


def _memory_backend_allowed() -> bool:
    """Allow env-driven memory backend only in test context."""
    return "pytest" in sys.modules


def _resolve_backend_name(raw_value: Any) -> str:
    value = str(raw_value or "").strip().lower()
    if value == "memory" and _memory_backend_allowed():
        return "memory"
    return "db"


def _build_default_repository() -> PushQueueRepository:
    backend = _resolve_backend_name(os.getenv("PUSH_QUEUE_BACKEND"))
    if backend == "memory":
        return InMemoryPushQueueRepository()
    return SqlModelPushQueueRepository()


repository: PushQueueRepository = _build_default_repository()


def get_push_queue_backend_name() -> str:
    if isinstance(repository, SqlModelPushQueueRepository):
        return "db"
    return "memory"


def ensure_push_repository_from_env(
    session_factory: Optional[Callable[[], Session]] = None,
) -> str:
    backend = _resolve_backend_name(os.getenv("PUSH_QUEUE_BACKEND"))
    if backend == "db":
        if get_push_queue_backend_name() != "db" or session_factory is not None:
            use_database_push_repository(session_factory=session_factory)
        return get_push_queue_backend_name()

    if get_push_queue_backend_name() != "memory":
        use_in_memory_push_repository()
    return get_push_queue_backend_name()


def set_push_queue_repository(new_repository: PushQueueRepository) -> None:
    global repository
    repository = new_repository


def use_in_memory_push_repository() -> None:
    set_push_queue_repository(InMemoryPushQueueRepository())


def use_database_push_repository(session_factory: Optional[Callable[[], Session]] = None) -> None:
    set_push_queue_repository(SqlModelPushQueueRepository(session_factory=session_factory))


def reset_push_storage() -> None:
    repository.reset()


def register_inventory_review_task(
    inventory_id: int,
    inventory_name: str,
    merchant_name: str,
    source: str = "inventory_import",
) -> dict[str, Any]:
    return repository.register_review_task(
        inventory_id=inventory_id,
        inventory_name=inventory_name,
        merchant_name=merchant_name,
        source=source,
    )


def approve_inventory_review_task(review_id: int, reviewed_by: str) -> Optional[dict[str, Any]]:
    return repository.approve_review_task(review_id=review_id, reviewed_by=reviewed_by)


def list_review_tasks() -> list[dict[str, Any]]:
    return repository.list_review_tasks()


def enqueue_push_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    return repository.enqueue_campaign(payload)


def cancel_push_campaign(campaign_id: int, cancelled_by: str = "") -> dict[str, Any]:
    row = repository.cancel_campaign(campaign_id=int(campaign_id), cancelled_by=str(cancelled_by or ""))
    if row is None:
        raise ValueError("Push campaign not found.")
    return row


def process_push_queue(batch_size: int = 20) -> dict[str, int]:
    return repository.process_queue(batch_size=batch_size)


def list_push_campaigns() -> list[dict[str, Any]]:
    return repository.list_campaigns()


def list_audit_logs() -> list[dict[str, Any]]:
    return repository.list_audit_logs()
