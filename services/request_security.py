"""Request policy guard helpers for dispatcher-level auth/authz."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from services.security_errors import AuthRequiredError, PermissionDeniedError


@dataclass(frozen=True)
class RoutePolicy:
    method: str
    pattern: re.Pattern[str]
    require_auth: bool = True
    required_role: Optional[str] = None


_ROUTE_POLICIES: tuple[RoutePolicy, ...] = (
    RoutePolicy("POST", re.compile(r"^/api/v1/finance/manual-deposit$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/finance/deposits/manual$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/orders/\d+/refund$"), require_auth=True),
    RoutePolicy("PATCH", re.compile(r"^/api/v1/users/\d+/status$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/users/\d+/balance-adjustments$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/users/\d+/balance-adjust$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/inventory/libraries/import$"), require_auth=True),
    RoutePolicy("PATCH", re.compile(r"^/api/v1/inventory/libraries/\d+/price$"), require_auth=True),
    RoutePolicy("PATCH", re.compile(r"^/api/v1/inventory/libraries/\d+/status$"), require_auth=True),
    RoutePolicy("DELETE", re.compile(r"^/api/v1/inventory/libraries/\d+$"), require_auth=True),
    RoutePolicy("POST", re.compile(r"^/api/v1/push/reviews/\d+/approve$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("POST", re.compile(r"^/api/v1/push/campaigns$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("POST", re.compile(r"^/api/v1/push/campaigns/\d+/cancel$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("POST", re.compile(r"^/api/v1/admin/accounts$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("PUT", re.compile(r"^/api/v1/settings/default-usdt-address$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("PUT", re.compile(r"^/api/v1/settings/usdt-query-api$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("PUT", re.compile(r"^/api/v1/settings/bins-query-api$"), require_auth=True, required_role="super_admin"),
    RoutePolicy("PUT", re.compile(r"^/api/v1/settings/telegram-push$"), require_auth=True, required_role="super_admin"),
)


def _extract_actor_username(body: dict[str, Any]) -> str:
    for key in ("actor_username", "operator_username", "reviewed_by", "cancelled_by", "username"):
        value = str(body.get(key) or "").strip()
        if value:
            return value
    return ""


def _route_policy(method: str, path: str) -> Optional[RoutePolicy]:
    normalized_method = str(method or "").upper()
    normalized_path = str(path or "").strip()
    for item in _ROUTE_POLICIES:
        if item.method == normalized_method and item.pattern.fullmatch(normalized_path):
            return item
    return None


def resolve_actor_profile_for_policy(
    *,
    method: str,
    path: str,
    body: dict[str, Any],
    profile_lookup: Callable[[str], Optional[dict[str, Any]]],
) -> Optional[dict[str, Any]]:
    policy = _route_policy(method, path)
    if policy is None:
        return None

    actor_username = _extract_actor_username(body)
    if not actor_username:
        return None
    return profile_lookup(actor_username)


def enforce_route_policy(
    *,
    method: str,
    path: str,
    body: dict[str, Any],
    actor_profile: Optional[dict[str, Any]],
) -> None:
    policy = _route_policy(method, path)
    if policy is None:
        return

    actor_username = _extract_actor_username(body)
    if policy.require_auth and not actor_username:
        raise AuthRequiredError("Authenticated actor is required for this action.")

    if policy.require_auth:
        if actor_profile is None:
            raise AuthRequiredError("Authenticated actor profile is required for this action.")
        if not bool(actor_profile.get("is_active", True)):
            raise AuthRequiredError("Authenticated actor is inactive.")

    if policy.required_role:
        role_value = str(actor_profile.get("role") if actor_profile else "")
        if role_value != policy.required_role:
            if policy.required_role == "super_admin":
                raise PermissionDeniedError("Only super admin can perform this action.")
            raise PermissionDeniedError("Actor does not have required role.")
