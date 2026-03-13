"""HTTP-like API client wrappers for export task domain."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from services.http_api_client import request_json


def ensure_export_task_repository_from_env(
    *,
    session_factory: Optional[Any] = None,
) -> str:
    del session_factory
    data = request_json("POST", "/api/v1/export/repository/ensure")
    if isinstance(data, dict):
        return str(data.get("backend") or "")
    return ""


def create_export_task(
    task_type: str,
    operator_id: Optional[int],
    filters_json: Any,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/export/tasks",
        {
            "task_type": task_type,
            "operator_id": operator_id,
            "filters_json": filters_json,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def update_export_task(
    task_id: int | str,
    *,
    session_factory: Optional[Any] = None,
    **fields: Any,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/export/tasks/{int(task_id)}",
        dict(fields),
    )
    return dict(data) if isinstance(data, dict) and data else None


def list_export_tasks(
    *,
    task_type: Optional[str] = None,
    limit: int = 20,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    payload: dict[str, Any] = {"limit": int(limit)}
    if task_type is not None and str(task_type).strip():
        payload["task_type"] = str(task_type)
    data = request_json("GET", "/api/v1/export/tasks", payload)
    return list(data) if isinstance(data, list) else []


def poll_export_task_snapshot(
    task_id: int | str,
    *,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json("GET", f"/api/v1/export/tasks/{int(task_id)}/snapshot")
    return dict(data) if isinstance(data, dict) and data else None


def resolve_export_download_payload(
    task_id: int | str,
    exports_root: str | Path | None = None,
    *,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    payload: dict[str, Any] | None = None
    if exports_root is not None:
        payload = {"exports_root": str(exports_root)}
    data = request_json(
        "GET",
        f"/api/v1/export/tasks/{int(task_id)}/download",
        payload,
    )
    return dict(data) if isinstance(data, dict) and data else None
