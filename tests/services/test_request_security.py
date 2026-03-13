from __future__ import annotations

import pytest


def test_enforce_route_policy_requires_actor_for_protected_write():
    from services.request_security import enforce_route_policy
    from services.security_errors import AuthRequiredError

    with pytest.raises(AuthRequiredError, match="actor"):
        enforce_route_policy(
            method="POST",
            path="/api/v1/finance/deposits/manual",
            body={},
            actor_profile=None,
        )


def test_enforce_route_policy_rejects_non_super_admin_for_settings_update():
    from services.request_security import enforce_route_policy
    from services.security_errors import PermissionDeniedError

    with pytest.raises(PermissionDeniedError, match="super admin"):
        enforce_route_policy(
            method="PUT",
            path="/api/v1/settings/default-usdt-address",
            body={"operator_username": "agent1"},
            actor_profile={"username": "agent1", "role": "agent", "is_active": True},
        )


def test_enforce_route_policy_allows_super_admin_for_settings_update():
    from services.request_security import enforce_route_policy

    enforce_route_policy(
        method="PUT",
        path="/api/v1/settings/default-usdt-address",
        body={"operator_username": "admin"},
        actor_profile={"username": "admin", "role": "super_admin", "is_active": True},
    )
