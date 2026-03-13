"""HTTP-like API client wrappers for push queue domain."""

from __future__ import annotations

from typing import Any, Optional

from services.http_api_client import request_json


def ensure_push_repository_from_env(
    *,
    session_factory: Optional[Any] = None,
) -> str:
    del session_factory
    data = request_json("POST", "/api/v1/push/repository/ensure")
    if isinstance(data, dict):
        return str(data.get("backend") or "")
    return ""


def reset_push_storage(
    *,
    session_factory: Optional[Any] = None,
) -> None:
    del session_factory
    request_json("POST", "/api/v1/push/reset")


def register_inventory_review_task(
    *,
    inventory_id: int,
    inventory_name: str,
    merchant_name: str,
    source: str = "inventory_import",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        "/api/v1/push/reviews",
        {
            "inventory_id": int(inventory_id),
            "inventory_name": inventory_name,
            "merchant_name": merchant_name,
            "source": source,
        },
    )
    return dict(data) if isinstance(data, dict) else {}


def approve_inventory_review_task(
    *,
    review_id: int,
    reviewed_by: str,
    session_factory: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    del session_factory
    data = request_json(
        "PATCH",
        f"/api/v1/push/reviews/{int(review_id)}/approve",
        {"reviewed_by": reviewed_by},
    )
    return dict(data) if isinstance(data, dict) and data else None


def list_review_tasks(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/push/reviews")
    return list(data) if isinstance(data, list) else []


def enqueue_push_campaign(
    payload: dict[str, Any],
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json("POST", "/api/v1/push/campaigns", dict(payload))
    return dict(data) if isinstance(data, dict) else {}


def process_push_queue(
    batch_size: int = 20,
    *,
    session_factory: Optional[Any] = None,
) -> dict[str, int]:
    del session_factory
    data = request_json("POST", "/api/v1/push/process", {"batch_size": int(batch_size)})
    if not isinstance(data, dict):
        return {"processed": 0, "sent": 0}
    return {
        "processed": int(data.get("processed") or 0),
        "sent": int(data.get("sent") or 0),
    }


def list_push_campaigns(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/push/campaigns")
    return list(data) if isinstance(data, list) else []


def cancel_push_campaign(
    campaign_id: int,
    *,
    cancelled_by: str = "",
    session_factory: Optional[Any] = None,
) -> dict[str, Any]:
    del session_factory
    data = request_json(
        "POST",
        f"/api/v1/push/campaigns/{int(campaign_id)}/cancel",
        {"cancelled_by": str(cancelled_by or "")},
    )
    return dict(data) if isinstance(data, dict) else {}


def list_audit_logs(
    *,
    session_factory: Optional[Any] = None,
) -> list[dict[str, Any]]:
    del session_factory
    data = request_json("GET", "/api/v1/push/audits")
    return list(data) if isinstance(data, list) else []
