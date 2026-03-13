"""Reflex-native API client for phase-2 state integration."""

from __future__ import annotations

from typing import Any, Optional

from services.reflex_api import dispatch_request


def request_json(
    method: str,
    path: str,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any] | list[Any]:
    """Call phase-2 Reflex dispatcher and return parsed payload."""
    return dispatch_request(method=method, path=path, payload=payload)
