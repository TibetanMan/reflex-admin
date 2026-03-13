"""Export task persistence adapters for memory and SQLModel backends."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Optional, Protocol

from sqlalchemy import delete
from sqlmodel import Session, select

from shared.models.user_export import ExportTask, ExportTaskStatus, ExportTaskType


ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(ISO_DATETIME_FORMAT)
    return str(value)


def _normalize_task_type(value: Any) -> ExportTaskType:
    text = str(value or ExportTaskType.ORDER.value).strip().lower()
    if text == ExportTaskType.USER.value:
        return ExportTaskType.USER
    return ExportTaskType.ORDER


def _normalize_status(value: Any) -> ExportTaskStatus:
    text = str(value or ExportTaskStatus.PENDING.value).strip().lower()
    for status in ExportTaskStatus:
        if text == status.value:
            return status
    return ExportTaskStatus.PENDING


def _coerce_filters_json(filters_json: Any) -> str:
    if isinstance(filters_json, str):
        return filters_json
    if isinstance(filters_json, dict):
        return json.dumps(filters_json, ensure_ascii=False)
    return "{}"


def _coerce_optional_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class ExportTaskRepository(Protocol):
    """Repository contract for export task persistence."""

    def reset(self) -> None: ...

    def create_task(
        self,
        task_type: str,
        operator_id: Optional[int],
        filters_json: Any,
    ) -> dict[str, Any]: ...

    def update_task(self, task_id: int | str, **fields: Any) -> Optional[dict[str, Any]]: ...

    def get_task(self, task_id: int | str) -> Optional[dict[str, Any]]: ...

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...


class InMemoryExportTaskRepository:
    """In-memory export task repository for local development and tests."""

    def __init__(self):
        self._lock = RLock()
        self._seq = 1
        self._tasks: dict[int, dict[str, Any]] = {}

    def reset(self) -> None:
        with self._lock:
            self._seq = 1
            self._tasks = {}

    def create_task(
        self,
        task_type: str,
        operator_id: Optional[int],
        filters_json: Any,
    ) -> dict[str, Any]:
        with self._lock:
            row = {
                "id": self._seq,
                "type": _normalize_task_type(task_type).value,
                "operator_id": int(operator_id) if operator_id is not None else None,
                "filters_json": _coerce_filters_json(filters_json),
                "status": ExportTaskStatus.PENDING.value,
                "progress": 0,
                "total_records": 0,
                "processed_records": 0,
                "file_path": "",
                "file_name": "",
                "error_message": "",
                "created_at": _to_text(datetime.now()),
                "finished_at": "",
            }
            self._tasks[self._seq] = row
            self._seq += 1
            return dict(row)

    def update_task(self, task_id: int | str, **fields: Any) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._tasks.get(int(task_id))
            if row is None:
                return None

            if "type" in fields:
                row["type"] = _normalize_task_type(fields["type"]).value
            if "operator_id" in fields:
                value = fields["operator_id"]
                row["operator_id"] = int(value) if value is not None else None
            if "filters_json" in fields:
                row["filters_json"] = _coerce_filters_json(fields["filters_json"])
            if "status" in fields:
                row["status"] = _normalize_status(fields["status"]).value
            if "progress" in fields:
                row["progress"] = max(0, min(100, int(fields["progress"])))
            if "total_records" in fields:
                row["total_records"] = max(0, int(fields["total_records"]))
            if "processed_records" in fields:
                row["processed_records"] = max(0, int(fields["processed_records"]))
            if "file_path" in fields:
                row["file_path"] = str(fields["file_path"] or "")
            if "file_name" in fields:
                row["file_name"] = str(fields["file_name"] or "")
            if "error_message" in fields:
                row["error_message"] = str(fields["error_message"] or "")
            if "finished_at" in fields:
                row["finished_at"] = _to_text(_coerce_optional_datetime(fields["finished_at"]))

            if row["status"] in TERMINAL_STATUSES and not row["finished_at"]:
                row["finished_at"] = _to_text(datetime.now())

            return dict(row)

    def get_task(self, task_id: int | str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._tasks.get(int(task_id))
            return dict(row) if row is not None else None

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._tasks.values())
            if task_type:
                normalized = _normalize_task_type(task_type).value
                rows = [row for row in rows if str(row.get("type")) == normalized]
            rows = sorted(rows, key=lambda item: int(item.get("id", 0)), reverse=True)
            return [dict(row) for row in rows[: max(1, int(limit))]]


class SqlModelExportTaskRepository:
    """SQLModel-backed repository for export task persistence."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        if session_factory is None:
            from shared.database import get_db_session

            self._session_factory = get_db_session
        else:
            self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def _to_dict(self, row: ExportTask) -> dict[str, Any]:
        return {
            "id": int(row.id or 0),
            "type": str(row.type.value if hasattr(row.type, "value") else row.type),
            "operator_id": int(row.operator_id) if row.operator_id is not None else None,
            "filters_json": str(row.filters_json or "{}"),
            "status": str(row.status.value if hasattr(row.status, "value") else row.status),
            "progress": int(row.progress or 0),
            "total_records": int(row.total_records or 0),
            "processed_records": int(row.processed_records or 0),
            "file_path": str(row.file_path or ""),
            "file_name": str(row.file_name or ""),
            "error_message": str(row.error_message or ""),
            "created_at": _to_text(row.created_at),
            "finished_at": _to_text(row.finished_at),
        }

    def reset(self) -> None:
        session = self._session()
        try:
            session.exec(delete(ExportTask))
            session.commit()
        finally:
            session.close()

    def create_task(
        self,
        task_type: str,
        operator_id: Optional[int],
        filters_json: Any,
    ) -> dict[str, Any]:
        session = self._session()
        try:
            row = ExportTask(
                type=_normalize_task_type(task_type),
                operator_id=int(operator_id) if operator_id is not None else None,
                filters_json=_coerce_filters_json(filters_json),
                status=ExportTaskStatus.PENDING,
                progress=0,
                total_records=0,
                processed_records=0,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_task(self, task_id: int | str, **fields: Any) -> Optional[dict[str, Any]]:
        session = self._session()
        try:
            row = session.get(ExportTask, int(task_id))
            if row is None:
                return None

            if "type" in fields:
                row.type = _normalize_task_type(fields["type"])
            if "operator_id" in fields:
                value = fields["operator_id"]
                row.operator_id = int(value) if value is not None else None
            if "filters_json" in fields:
                row.filters_json = _coerce_filters_json(fields["filters_json"])
            if "status" in fields:
                row.status = _normalize_status(fields["status"])
            if "progress" in fields:
                row.progress = max(0, min(100, int(fields["progress"])))
            if "total_records" in fields:
                row.total_records = max(0, int(fields["total_records"]))
            if "processed_records" in fields:
                row.processed_records = max(0, int(fields["processed_records"]))
            if "file_path" in fields:
                row.file_path = str(fields["file_path"] or "")
            if "file_name" in fields:
                row.file_name = str(fields["file_name"] or "")
            if "error_message" in fields:
                row.error_message = str(fields["error_message"] or "")

            if "finished_at" in fields:
                row.finished_at = _coerce_optional_datetime(fields["finished_at"])
            else:
                status_text = (
                    row.status.value if hasattr(row.status, "value") else str(row.status)
                ).lower()
                if status_text in TERMINAL_STATUSES and row.finished_at is None:
                    row.finished_at = datetime.now()

            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_task(self, task_id: int | str) -> Optional[dict[str, Any]]:
        session = self._session()
        try:
            row = session.get(ExportTask, int(task_id))
            if row is None:
                return None
            return self._to_dict(row)
        finally:
            session.close()

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        session = self._session()
        try:
            stmt = select(ExportTask)
            if task_type:
                stmt = stmt.where(ExportTask.type == _normalize_task_type(task_type))
            stmt = stmt.order_by(ExportTask.id.desc()).limit(max(1, int(limit)))
            rows = list(session.exec(stmt).all())
            return [self._to_dict(row) for row in rows]
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


def _build_default_repository() -> ExportTaskRepository:
    backend = _resolve_backend_name(os.getenv("EXPORT_TASK_BACKEND"))
    if backend == "memory":
        return InMemoryExportTaskRepository()
    return SqlModelExportTaskRepository()


repository: ExportTaskRepository = _build_default_repository()


def set_export_task_repository(new_repository: ExportTaskRepository) -> None:
    global repository
    repository = new_repository


def use_in_memory_export_task_repository() -> None:
    set_export_task_repository(InMemoryExportTaskRepository())


def use_database_export_task_repository(
    session_factory: Optional[Callable[[], Session]] = None,
) -> None:
    set_export_task_repository(SqlModelExportTaskRepository(session_factory=session_factory))


def get_export_task_backend_name() -> str:
    if isinstance(repository, SqlModelExportTaskRepository):
        return "db"
    return "memory"


def ensure_export_task_repository_from_env(
    session_factory: Optional[Callable[[], Session]] = None,
) -> str:
    backend = _resolve_backend_name(os.getenv("EXPORT_TASK_BACKEND"))
    if backend == "db":
        if get_export_task_backend_name() != "db" or session_factory is not None:
            use_database_export_task_repository(session_factory=session_factory)
        return get_export_task_backend_name()

    if get_export_task_backend_name() != "memory":
        use_in_memory_export_task_repository()
    return get_export_task_backend_name()


def reset_export_task_storage() -> None:
    repository.reset()


def create_export_task(
    task_type: str,
    operator_id: Optional[int],
    filters_json: Any,
) -> dict[str, Any]:
    return repository.create_task(
        task_type=task_type,
        operator_id=operator_id,
        filters_json=filters_json,
    )


def update_export_task(task_id: int | str, **fields: Any) -> Optional[dict[str, Any]]:
    return repository.update_task(task_id=task_id, **fields)


def get_export_task(task_id: int | str) -> Optional[dict[str, Any]]:
    return repository.get_task(task_id=task_id)


def list_export_tasks(
    task_type: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return repository.list_tasks(task_type=task_type, limit=limit)


def poll_export_task_snapshot(task_id: int | str) -> Optional[dict[str, Any]]:
    task = get_export_task(task_id)
    if task is None:
        return None

    status = str(task.get("status") or "")
    return {
        "id": int(task.get("id") or 0),
        "type": str(task.get("type") or ""),
        "status": status,
        "progress": int(task.get("progress") or 0),
        "total_records": int(task.get("total_records") or 0),
        "processed_records": int(task.get("processed_records") or 0),
        "file_name": str(task.get("file_name") or ""),
        "file_path": str(task.get("file_path") or ""),
        "error_message": str(task.get("error_message") or ""),
        "finished_at": str(task.get("finished_at") or ""),
        "is_terminal": status in TERMINAL_STATUSES,
    }


def resolve_export_download_payload(
    task_id: int | str,
    exports_root: str | Path | None = None,
) -> Optional[dict[str, Any]]:
    task = get_export_task(task_id)
    if task is None:
        return None

    file_path = str(task.get("file_path") or "").strip()
    if not file_path:
        return None
    file_name = str(task.get("file_name") or "").strip()

    root = Path(exports_root) if exports_root is not None else Path("uploaded_files") / "exports"
    try:
        root_resolved = root.resolve()
        resolved = Path(file_path).resolve()
    except Exception:
        return None

    if root_resolved not in resolved.parents:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None

    return {
        "task_id": int(task["id"]),
        "file_path": str(resolved),
        "file_name": file_name or resolved.name,
    }
