from __future__ import annotations

import importlib
import pytest

def test_settings_dispatch_returns_service_payload(monkeypatch):
    api_module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        api_module,
        "get_settings_snapshot_service",
        lambda: {"default_usdt_address": "T-PHASE2-SETTINGS"},
    )

    payload = api_module.dispatch_request("GET", "/api/v1/settings")
    assert payload["default_usdt_address"] == "T-PHASE2-SETTINGS"


def test_profile_dispatch_returns_service_payload(monkeypatch):
    api_module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        api_module,
        "get_profile_snapshot_service",
        lambda username="": {"username": username or "admin", "display_name": "Super Admin"},
    )

    payload = api_module.dispatch_request("GET", "/api/v1/profile")
    assert payload["username"] == "admin"


def test_inventory_dispatch_returns_service_payload(monkeypatch):
    api_module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        api_module,
        "list_inventory_snapshot_service",
        lambda: [{"id": 1, "name": "Inventory A"}],
    )

    payload = api_module.dispatch_request("GET", "/api/v1/inventory/libraries")
    assert payload[0]["name"] == "Inventory A"


def test_settings_api_client_calls_http_route(monkeypatch):
    module = importlib.import_module("services.settings_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"default_usdt_address": "T-API-CLIENT"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    row = module.get_settings_snapshot()
    assert row["default_usdt_address"] == "T-API-CLIENT"
    assert captured == {"method": "GET", "path": "/api/v1/settings", "payload": None}


def test_profile_api_client_calls_http_route(monkeypatch):
    module = importlib.import_module("services.profile_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"username": "admin", "display_name": "Phase2"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    row = module.get_profile_snapshot(username="admin")
    assert row["display_name"] == "Phase2"
    assert captured == {
        "method": "GET",
        "path": "/api/v1/profile",
        "payload": {"username": "admin"},
    }


def test_inventory_api_client_calls_http_route(monkeypatch):
    module = importlib.import_module("services.inventory_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return [{"id": 9, "name": "Phase2 Inventory"}]

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    rows = module.list_inventory_snapshot()
    assert rows[0]["id"] == 9
    assert captured == {
        "method": "GET",
        "path": "/api/v1/inventory/libraries",
        "payload": None,
    }


def test_inventory_api_client_toggle_status_passes_operator(monkeypatch):
    module = importlib.import_module("services.inventory_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"id": 10, "status": "inactive"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    row = module.toggle_inventory_status(inventory_id=10, operator_username="admin")

    assert row["status"] == "inactive"
    assert captured == {
        "method": "PATCH",
        "path": "/api/v1/inventory/libraries/10/status",
        "payload": {"operator_username": "admin"},
    }


def test_inventory_status_dispatch_routes_operator_to_service(monkeypatch):
    module = importlib.import_module("services.reflex_api")
    captured: dict[str, object] = {}

    def _fake_toggle_inventory_status_service(**kwargs):
        captured.update(kwargs)
        return {"id": kwargs["inventory_id"], "status": "inactive"}

    monkeypatch.setattr(
        module,
        "toggle_inventory_status_service",
        _fake_toggle_inventory_status_service,
    )

    row = module.dispatch_request(
        "PATCH",
        "/api/v1/inventory/libraries/9/status",
        {"operator_username": "admin"},
    )

    assert row["status"] == "inactive"
    assert captured == {"inventory_id": 9, "operator_username": "admin"}


def test_dashboard_api_client_calls_http_route(monkeypatch):
    module = importlib.import_module("services.dashboard_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"today_sales": 123.0}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    row = module.get_dashboard_snapshot()
    assert row["today_sales"] == 123.0
    assert captured == {
        "method": "GET",
        "path": "/api/v1/dashboard/summary",
        "payload": None,
    }


def test_dashboard_dispatch_exposes_extended_query_routes(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(module, "list_recent_orders_service", lambda limit=10: [{"id": "ORD-1", "limit": limit}])
    monkeypatch.setattr(
        module,
        "list_recent_deposits_service",
        lambda limit=10: [{"id": "DEP-1", "limit": limit}],
    )
    monkeypatch.setattr(
        module,
        "list_top_categories_service",
        lambda limit=10: [{"name": "US VISA", "limit": limit}],
    )
    monkeypatch.setattr(module, "list_bot_status_service", lambda limit=10: [{"name": "Bot A", "limit": limit}])

    orders = module.dispatch_request("GET", "/api/v1/dashboard/recent-orders", {"limit": 3})
    deposits = module.dispatch_request("GET", "/api/v1/dashboard/recent-deposits", {"limit": 2})
    categories = module.dispatch_request("GET", "/api/v1/dashboard/top-categories", {"limit": 4})
    bot_status = module.dispatch_request("GET", "/api/v1/dashboard/bot-status", {"limit": 5})

    assert orders[0]["limit"] == 3
    assert deposits[0]["limit"] == 2
    assert categories[0]["limit"] == 4
    assert bot_status[0]["limit"] == 5


def test_dashboard_api_client_calls_extended_routes(monkeypatch):
    module = importlib.import_module("services.dashboard_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        return [{"id": path, "payload": payload}]

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    recent_orders = module.list_recent_orders(limit=3)
    recent_deposits = module.list_recent_deposits(limit=2)
    top_categories = module.list_top_categories(limit=4)
    bot_status = module.list_bot_status(limit=5)

    assert recent_orders[0]["id"] == "/api/v1/dashboard/recent-orders"
    assert recent_deposits[0]["id"] == "/api/v1/dashboard/recent-deposits"
    assert top_categories[0]["id"] == "/api/v1/dashboard/top-categories"
    assert bot_status[0]["id"] == "/api/v1/dashboard/bot-status"
    assert calls[0]["payload"] == {"limit": 3}
    assert calls[1]["payload"] == {"limit": 2}
    assert calls[2]["payload"] == {"limit": 4}
    assert calls[3]["payload"] == {"limit": 5}


def test_bot_api_client_calls_http_route(monkeypatch):
    module = importlib.import_module("services.bot_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return [{"id": 1, "name": "API Bot"}]

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    rows = module.list_bots_snapshot()

    assert rows[0]["name"] == "API Bot"
    assert captured == {
        "method": "GET",
        "path": "/api/v1/bots",
        "payload": None,
    }


def test_reflex_dispatch_exposes_management_routes(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "list_agents_snapshot_service",
        lambda: [{"id": 1, "name": "Agent A"}],
    )
    monkeypatch.setattr(
        module,
        "list_merchants_snapshot_service",
        lambda: [{"id": 2, "name": "Merchant B"}],
    )

    agents = module.dispatch_request("GET", "/api/v1/agents")
    merchants = module.dispatch_request("GET", "/api/v1/merchants")

    assert agents[0]["name"] == "Agent A"
    assert merchants[0]["name"] == "Merchant B"


def test_auth_dispatch_returns_service_payload(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "authenticate_admin_service",
        lambda username, password: {"username": username, "ok": password == "admin123"},
    )

    payload = module.dispatch_request(
        "POST",
        "/api/v1/auth/login",
        {"username": "admin", "password": "admin123"},
    )
    assert payload["ok"] is True


def test_auth_session_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "get_admin_profile_service",
        lambda username="": {"username": username or "admin", "role": "super_admin"},
    )
    monkeypatch.setattr(
        module,
        "logout_admin_service",
        lambda username="": {"ok": True, "username": username},
    )
    monkeypatch.setattr(
        module,
        "refresh_admin_session_service",
        lambda username="": {
            "access_token": "access-x",
            "refresh_token": "refresh-x",
            "user": {"username": username or "admin"},
        },
    )

    me = module.dispatch_request("GET", "/api/v1/auth/me", {"username": "admin"})
    logged_out = module.dispatch_request("POST", "/api/v1/auth/logout", {"username": "admin"})
    refreshed = module.dispatch_request("POST", "/api/v1/auth/refresh", {"username": "admin"})

    assert me["username"] == "admin"
    assert logged_out["ok"] is True
    assert refreshed["user"]["username"] == "admin"


def test_finance_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(module, "list_finance_deposits_service", lambda: [{"id": 1}])
    monkeypatch.setattr(module, "list_finance_wallets_service", lambda: [{"id": 2}])
    monkeypatch.setattr(module, "reconcile_finance_deposits_service", lambda limit=100: {"completed": 1, "limit": limit})
    monkeypatch.setattr(
        module,
        "create_manual_deposit_service",
        lambda **kwargs: {"id": 3, "operator": kwargs["operator_username"]},
    )

    deposits = module.dispatch_request("GET", "/api/v1/finance/deposits")
    wallets = module.dispatch_request("GET", "/api/v1/finance/wallets")
    created = module.dispatch_request(
        "POST",
        "/api/v1/finance/manual-deposit",
        {
            "user_identifier": "10001",
            "amount": "9.99",
            "remark": "manual",
            "operator_username": "admin",
        },
    )
    synced = module.dispatch_request(
        "POST",
        "/api/v1/finance/deposits/reconcile",
        {"limit": 9},
    )

    assert deposits[0]["id"] == 1
    assert wallets[0]["id"] == 2
    assert created["operator"] == "admin"
    assert synced["completed"] == 1
    assert synced["limit"] == 9


def test_finance_manual_deposit_route_propagates_wallet_error(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    def _raise_wallet_error(**kwargs):
        del kwargs
        raise ValueError("Current bot has no configured receiving wallet.")

    monkeypatch.setattr(module, "create_manual_deposit_service", _raise_wallet_error, raising=False)

    with pytest.raises(ValueError, match="wallet"):
        module.dispatch_request(
            "POST",
            "/api/v1/finance/deposits/manual",
            {
                "actor_username": "admin",
                "user_identifier": "10001",
                "amount": "9.99",
                "remark": "manual",
                "operator_username": "admin",
            },
        )


def test_dispatch_rejects_missing_actor_on_sensitive_write():
    module = importlib.import_module("services.reflex_api")

    with pytest.raises(PermissionError):
        module.dispatch_request(
            "POST",
            "/api/v1/finance/deposits/manual",
            {
                "user_identifier": "10001",
                "amount": "9.99",
                "remark": "manual",
            },
        )


def test_dispatch_rejects_non_super_admin_for_settings_write(monkeypatch):
    module = importlib.import_module("services.reflex_api")
    monkeypatch.setattr(
        module,
        "get_admin_profile_service",
        lambda username="": {"username": username, "role": "agent", "is_active": True},
    )

    with pytest.raises(PermissionError):
        module.dispatch_request(
            "PUT",
            "/api/v1/settings/default-usdt-address",
            {"address": "T-NEW-ADDR", "operator_username": "agent1"},
        )


def test_order_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(module, "list_orders_snapshot_service", lambda: [{"id": 11}])
    monkeypatch.setattr(
        module,
        "refund_order_service",
        lambda **kwargs: {"id": kwargs["order_id"], "status": "refunded"},
    )

    rows = module.dispatch_request("GET", "/api/v1/orders")
    refunded = module.dispatch_request(
        "POST",
        "/api/v1/orders/11/refund",
        {"reason": "test", "operator_username": "admin"},
    )

    assert rows[0]["id"] == 11
    assert refunded["status"] == "refunded"


def test_user_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(module, "list_users_snapshot_service", lambda: [{"id": 21}])
    monkeypatch.setattr(
        module,
        "toggle_user_ban_service",
        lambda **kwargs: {"id": kwargs["user_id"], "status": "banned"},
    )
    monkeypatch.setattr(
        module,
        "adjust_user_balance_service",
        lambda **kwargs: {"id": kwargs["user_id"], "balance": 19.8},
    )

    users = module.dispatch_request("GET", "/api/v1/users")
    banned = module.dispatch_request(
        "PATCH",
        "/api/v1/users/21/ban",
        {"operator_username": "admin"},
    )
    adjusted = module.dispatch_request(
        "POST",
        "/api/v1/users/21/balance-adjust",
        {
            "action": "credit",
            "amount": "9.90",
            "remark": "test",
            "source_bot_name": "Main Bot",
            "request_id": "req-1",
            "operator_username": "admin",
        },
    )

    assert users[0]["id"] == 21
    assert banned["status"] == "banned"
    assert adjusted["balance"] == 19.8


def test_push_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")
    monkeypatch.setattr(
        module,
        "get_admin_profile_service",
        lambda username="": {"username": username, "role": "super_admin", "is_active": True},
    )

    monkeypatch.setattr(module, "list_review_tasks_service", lambda: [{"id": 31}])
    monkeypatch.setattr(
        module,
        "approve_inventory_review_task_service",
        lambda review_id, reviewed_by: {"id": review_id, "reviewed_by": reviewed_by},
    )
    monkeypatch.setattr(
        module,
        "enqueue_push_campaign_service",
        lambda payload: {"id": 32, "status": "queued", "scope": payload.get("scope")},
    )
    monkeypatch.setattr(module, "process_push_queue_service", lambda batch_size=20: {"sent": 1})
    monkeypatch.setattr(module, "list_push_campaigns_service", lambda: [{"id": 32}])
    monkeypatch.setattr(module, "list_push_audit_logs_service", lambda: [{"id": 33}])

    reviews = module.dispatch_request("GET", "/api/v1/push/reviews")
    approved = module.dispatch_request(
        "PATCH",
        "/api/v1/push/reviews/31/approve",
        {"reviewed_by": "super_admin"},
    )
    campaign = module.dispatch_request(
        "POST",
        "/api/v1/push/campaigns",
        {"scope": "inventory", "actor_username": "super_admin"},
    )
    result = module.dispatch_request("POST", "/api/v1/push/process", {"batch_size": 10})
    campaigns = module.dispatch_request("GET", "/api/v1/push/campaigns")
    audits = module.dispatch_request("GET", "/api/v1/push/audits")

    assert reviews[0]["id"] == 31
    assert approved["reviewed_by"] == "super_admin"
    assert campaign["status"] == "queued"
    assert result["sent"] == 1
    assert campaigns[0]["id"] == 32
    assert audits[0]["id"] == 33


def test_auth_api_client_calls_route(monkeypatch):
    module = importlib.import_module("services.auth_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"username": "admin"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    row = module.authenticate_admin("admin", "admin123")

    assert row["username"] == "admin"
    assert captured == {
        "method": "POST",
        "path": "/api/v1/auth/login",
        "payload": {"username": "admin", "password": "admin123"},
    }


def test_auth_api_client_calls_session_routes(monkeypatch):
    module = importlib.import_module("services.auth_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if path.endswith("/me"):
            return {"username": "admin"}
        if path.endswith("/logout"):
            return {"ok": True}
        return {"access_token": "access-x", "refresh_token": "refresh-x"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    me = module.get_auth_me("admin")
    logged_out = module.logout_admin("admin")
    refreshed = module.refresh_admin_session("admin")

    assert me["username"] == "admin"
    assert logged_out["ok"] is True
    assert refreshed["access_token"] == "access-x"
    assert calls[0] == {
        "method": "GET",
        "path": "/api/v1/auth/me",
        "payload": {"username": "admin"},
    }
    assert calls[1]["path"] == "/api/v1/auth/logout"
    assert calls[2]["path"] == "/api/v1/auth/refresh"


def test_finance_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.finance_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if path.endswith("/reconcile"):
            return {"completed": 1}
        if path.endswith("/deposits"):
            return [{"id": 1}]
        if path.endswith("/wallets"):
            return [{"id": 2}]
        return {"id": 3}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    rows = module.list_finance_deposits()
    wallets = module.list_finance_wallets()
    created = module.create_manual_deposit(
        user_identifier="10001",
        amount="9.99",
        remark="manual",
        operator_username="admin",
    )
    synced = module.reconcile_finance_deposits(limit=9)

    assert rows[0]["id"] == 1
    assert wallets[0]["id"] == 2
    assert created["id"] == 3
    assert synced["completed"] == 1
    assert calls[2]["path"] == "/api/v1/finance/manual-deposit"
    assert calls[3] == {
        "method": "POST",
        "path": "/api/v1/finance/deposits/reconcile",
        "payload": {"limit": 9},
    }


def test_order_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.order_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        if method == "GET":
            return [{"id": 1}]
        return {"id": 1, "status": "refunded"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    rows = module.list_orders_snapshot()
    row = module.refund_order(order_id=1, reason="duplicate", operator_username="admin")

    assert rows[0]["id"] == 1
    assert row["status"] == "refunded"
    assert captured["path"] == "/api/v1/orders/1/refund"


def test_user_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.user_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        if method == "GET":
            return [{"id": 1}]
        return {"id": 1, "status": "banned"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    rows = module.list_users_snapshot()
    row = module.toggle_user_ban(user_id=1, operator_username="admin")

    assert rows[0]["id"] == 1
    assert row["status"] == "banned"
    assert captured["path"] == "/api/v1/users/1/ban"


def test_push_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.push_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        if method == "GET":
            return [{"id": 1}]
        return {"id": 1}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    rows = module.list_push_campaigns()
    row = module.enqueue_push_campaign({"scope": "inventory"})

    assert rows[0]["id"] == 1
    assert row["id"] == 1
    assert captured["path"] == "/api/v1/push/campaigns"


def test_export_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(module, "ensure_export_task_repository_from_env_service", lambda: "db")
    monkeypatch.setattr(
        module,
        "create_export_task_service",
        lambda task_type, operator_id, filters_json: {"id": 41, "type": task_type},
    )
    monkeypatch.setattr(
        module,
        "list_export_tasks_service",
        lambda task_type=None, limit=20: [{"id": 41, "type": task_type or "order", "limit": limit}],
    )
    monkeypatch.setattr(
        module,
        "update_export_task_service",
        lambda task_id, **fields: {"id": int(task_id), **fields},
    )
    monkeypatch.setattr(
        module,
        "poll_export_task_snapshot_service",
        lambda task_id: {"id": int(task_id), "status": "processing", "progress": 55},
    )
    monkeypatch.setattr(
        module,
        "resolve_export_download_payload_service",
        lambda task_id, exports_root=None: {"task_id": int(task_id), "file_name": "exp.csv"},
    )

    ensured = module.dispatch_request("POST", "/api/v1/export/repository/ensure")
    created = module.dispatch_request(
        "POST",
        "/api/v1/export/tasks",
        {"task_type": "order", "operator_id": None, "filters_json": {"bot_name": "All"}},
    )
    rows = module.dispatch_request("GET", "/api/v1/export/tasks", {"task_type": "order", "limit": 8})
    updated = module.dispatch_request(
        "PATCH",
        "/api/v1/export/tasks/41",
        {"status": "completed", "progress": 100},
    )
    snapshot = module.dispatch_request("GET", "/api/v1/export/tasks/41/snapshot")
    download = module.dispatch_request("GET", "/api/v1/export/tasks/41/download")

    assert ensured["backend"] == "db"
    assert created["id"] == 41
    assert rows[0]["id"] == 41
    assert updated["status"] == "completed"
    assert snapshot["progress"] == 55
    assert download["file_name"] == "exp.csv"


def test_export_task_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.export_task_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if path == "/api/v1/export/repository/ensure":
            return {"backend": "db"}
        if path == "/api/v1/export/tasks" and method == "POST":
            return {"id": 1}
        if path == "/api/v1/export/tasks" and method == "GET":
            return [{"id": 1}]
        if path.endswith("/snapshot"):
            return {"id": 1, "status": "processing"}
        if path.endswith("/download"):
            return {"task_id": 1, "file_name": "exp.csv"}
        return {"id": 1, "status": "completed"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    backend = module.ensure_export_task_repository_from_env()
    created = module.create_export_task("order", None, {"bot_name": "All"})
    rows = module.list_export_tasks(task_type="order", limit=8)
    updated = module.update_export_task(1, status="completed")
    snapshot = module.poll_export_task_snapshot(1)
    payload = module.resolve_export_download_payload(1)

    assert backend == "db"
    assert created["id"] == 1
    assert rows[0]["id"] == 1
    assert updated["status"] == "completed"
    assert snapshot["status"] == "processing"
    assert payload["file_name"] == "exp.csv"
    assert calls[0]["path"] == "/api/v1/export/repository/ensure"


def test_order_dispatch_routes_detail_and_refresh(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "get_order_snapshot_service",
        lambda order_id: {"id": order_id, "order_no": "ORD-1"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "refresh_order_status_service",
        lambda order_id: {"id": order_id, "status": "completed"},
        raising=False,
    )

    detail = module.dispatch_request("GET", "/api/v1/orders/11")
    refreshed = module.dispatch_request("POST", "/api/v1/orders/11/refresh-status")

    assert detail["order_no"] == "ORD-1"
    assert refreshed["status"] == "completed"


def test_order_api_client_calls_detail_and_refresh_routes(monkeypatch):
    module = importlib.import_module("services.order_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if method == "GET":
            return {"id": 11}
        return {"id": 11, "status": "completed"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    detail = module.get_order_snapshot(11)
    refreshed = module.refresh_order_status(11)

    assert detail["id"] == 11
    assert refreshed["status"] == "completed"
    assert calls[0]["path"] == "/api/v1/orders/11"
    assert calls[1]["path"] == "/api/v1/orders/11/refresh-status"


def test_user_dispatch_routes_detail_and_records(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "get_user_snapshot_service",
        lambda user_id: {"id": user_id, "telegram_id": "777001"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_user_deposit_records_service",
        lambda user_id: [{"record_no": f"DEP-{user_id}"}],
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_user_purchase_records_service",
        lambda user_id: [{"order_no": f"ORD-{user_id}"}],
        raising=False,
    )

    detail = module.dispatch_request("GET", "/api/v1/users/21")
    deposits = module.dispatch_request("GET", "/api/v1/users/21/deposit-records")
    purchases = module.dispatch_request("GET", "/api/v1/users/21/purchase-records")

    assert detail["telegram_id"] == "777001"
    assert deposits[0]["record_no"] == "DEP-21"
    assert purchases[0]["order_no"] == "ORD-21"


def test_user_api_client_calls_detail_and_records_routes(monkeypatch):
    module = importlib.import_module("services.user_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if path.endswith("/deposit-records"):
            return [{"record_no": "DEP-1"}]
        if path.endswith("/purchase-records"):
            return [{"order_no": "ORD-1"}]
        return {"id": 1}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    detail = module.get_user_snapshot(1)
    deposits = module.list_user_deposit_records(1)
    purchases = module.list_user_purchase_records(1)

    assert detail["id"] == 1
    assert deposits[0]["record_no"] == "DEP-1"
    assert purchases[0]["order_no"] == "ORD-1"
    assert calls[0]["path"] == "/api/v1/users/1"
    assert calls[1]["path"] == "/api/v1/users/1/deposit-records"
    assert calls[2]["path"] == "/api/v1/users/1/purchase-records"


def test_finance_dispatch_routes_wallet_detail(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "get_finance_wallet_service",
        lambda wallet_id: {"id": wallet_id, "address": "TRX-1"},
        raising=False,
    )

    detail = module.dispatch_request("GET", "/api/v1/finance/wallets/5")
    assert detail["address"] == "TRX-1"


def test_finance_api_client_calls_wallet_detail_route(monkeypatch):
    module = importlib.import_module("services.finance_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"id": 5, "address": "TRX-5"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    row = module.get_finance_wallet(5)

    assert row["id"] == 5
    assert captured == {"method": "GET", "path": "/api/v1/finance/wallets/5", "payload": None}


def test_push_dispatch_routes_campaign_cancel(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "cancel_push_campaign_service",
        lambda campaign_id, cancelled_by: {
            "id": campaign_id,
            "status": "cancelled",
            "cancelled_by": cancelled_by,
        },
        raising=False,
    )

    row = module.dispatch_request(
        "POST",
        "/api/v1/push/campaigns/9/cancel",
        {"cancelled_by": "admin"},
    )
    assert row["status"] == "cancelled"
    assert row["cancelled_by"] == "admin"


def test_push_api_client_calls_campaign_cancel_route(monkeypatch):
    module = importlib.import_module("services.push_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"id": 9, "status": "cancelled"}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    row = module.cancel_push_campaign(9, cancelled_by="admin")

    assert row["status"] == "cancelled"
    assert captured["path"] == "/api/v1/push/campaigns/9/cancel"
    assert captured["payload"] == {"cancelled_by": "admin"}


def test_profile_dispatch_routes_password_update(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "update_profile_password_service",
        lambda username, old_password, new_password: {
            "ok": True,
            "username": username,
            "password_updated": old_password != new_password,
        },
        raising=False,
    )

    result = module.dispatch_request(
        "PATCH",
        "/api/v1/profile/password",
        {
            "username": "admin",
            "old_password": "admin123",
            "new_password": "admin456",
        },
    )
    assert result["ok"] is True
    assert result["password_updated"] is True


def test_profile_api_client_calls_password_update_route(monkeypatch):
    module = importlib.import_module("services.profile_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    result = module.update_profile_password(
        username="admin",
        old_password="admin123",
        new_password="admin456",
    )

    assert result["ok"] is True
    assert captured["method"] == "PATCH"
    assert captured["path"] == "/api/v1/profile/password"


def test_bot_side_dispatch_routes_to_services(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "list_bot_catalog_categories_service",
        lambda catalog_type="full", bot_id=None: [{"id": 1, "type": catalog_type, "bot_id": bot_id}],
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_bot_catalog_items_service",
        lambda **kwargs: {"items": [{"id": 2}], "page": kwargs.get("page", 1)},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_bot_bin_info_service",
        lambda bin_number: {"bin_number": bin_number, "country_code": "US"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_bot_merchants_service",
        lambda: [{"id": 7, "name": "Merchant"}],
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_bot_merchant_items_service",
        lambda merchant_id, page=1, page_size=20: {
            "merchant_id": merchant_id,
            "items": [{"id": 9}],
            "page": page,
            "page_size": page_size,
        },
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "add_bot_cart_item_service",
        lambda **kwargs: {"id": 31, "user_id": kwargs["user_id"]},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_bot_cart_service",
        lambda user_id: {"user_id": user_id, "items": []},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "remove_bot_cart_item_service",
        lambda **kwargs: {"ok": True, "id": kwargs["cart_item_id"]},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "checkout_bot_order_service",
        lambda user_id, bot_id=None: {"user_id": user_id, "bot_id": bot_id, "status": "completed"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_bot_orders_service",
        lambda user_id, page=1, page_size=20: {
            "orders": [{"id": 11}],
            "user_id": user_id,
            "page": page,
            "page_size": page_size,
        },
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_bot_deposit_service",
        lambda user_id, amount, bot_id=None: {
            "id": 51,
            "user_id": user_id,
            "amount": float(amount),
            "bot_id": bot_id,
        },
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_bot_deposit_service",
        lambda deposit_id, user_id, bot_id=None, sync_onchain=True: {
            "id": deposit_id,
            "user_id": user_id,
            "bot_id": bot_id,
            "sync_onchain": sync_onchain,
        },
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_bot_balance_service",
        lambda user_id: {"user_id": user_id, "balance": 9.9},
        raising=False,
    )

    categories = module.dispatch_request(
        "GET",
        "/api/v1/bot/catalog/categories",
        {"type": "full", "bot_id": 1},
    )
    items = module.dispatch_request(
        "GET",
        "/api/v1/bot/catalog/items",
        {"category_id": 3, "country": "US", "bin": "411111", "page": 2, "page_size": 5},
    )
    bin_row = module.dispatch_request("GET", "/api/v1/bot/bin/411111")
    merchants = module.dispatch_request("GET", "/api/v1/bot/merchants")
    merchant_items = module.dispatch_request(
        "GET",
        "/api/v1/bot/merchants/7/items",
        {"page": 3, "page_size": 6},
    )
    cart_created = module.dispatch_request(
        "POST",
        "/api/v1/bot/cart/items",
        {"user_id": 8, "category_id": 3, "quantity": 2},
    )
    cart = module.dispatch_request("GET", "/api/v1/bot/cart", {"user_id": 8})
    removed = module.dispatch_request(
        "DELETE",
        "/api/v1/bot/cart/items/31",
        {"user_id": 8},
    )
    checked_out = module.dispatch_request(
        "POST",
        "/api/v1/bot/orders/checkout",
        {"user_id": 8, "bot_id": 2},
    )
    orders = module.dispatch_request(
        "GET",
        "/api/v1/bot/orders",
        {"user_id": 8, "page": 2, "page_size": 10},
    )
    deposit_created = module.dispatch_request(
        "POST",
        "/api/v1/bot/deposits/create",
        {"user_id": 8, "bot_id": 2, "amount": "9.90"},
    )
    deposit = module.dispatch_request(
        "GET",
        "/api/v1/bot/deposits/51",
        {"user_id": 8},
    )
    balance = module.dispatch_request("GET", "/api/v1/bot/balance", {"user_id": 8})

    assert categories[0]["type"] == "full"
    assert items["page"] == 2
    assert bin_row["bin_number"] == "411111"
    assert merchants[0]["id"] == 7
    assert merchant_items["page_size"] == 6
    assert cart_created["user_id"] == 8
    assert cart["user_id"] == 8
    assert removed["ok"] is True
    assert checked_out["status"] == "completed"
    assert orders["page"] == 2
    assert deposit_created["amount"] == 9.9
    assert deposit["id"] == 51
    assert balance["balance"] == 9.9


def test_bot_side_api_client_calls_routes(monkeypatch):
    module = importlib.import_module("services.bot_side_api")
    calls: list[dict[str, object]] = []

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        calls.append({"method": method, "path": path, "payload": payload})
        if path.endswith("/cart/items") and method == "POST":
            return {"id": 31}
        if path.endswith("/categories"):
            return [{"id": 1}]
        if path.endswith("/items") and "/merchants/" not in path:
            return {"items": [{"id": 2}], "total": 1}
        if "/bot/bin/" in path:
            return {"bin_number": "411111"}
        if path.endswith("/merchants"):
            return [{"id": 7}]
        if "/merchants/" in path and path.endswith("/items"):
            return {"items": [{"id": 9}], "total": 1}
        if path.endswith("/cart") and method == "GET":
            return {"items": [], "total_amount": 0}
        if "/cart/items/" in path and method == "DELETE":
            return {"ok": True}
        if path.endswith("/checkout"):
            return {"id": 11, "status": "completed"}
        if path.endswith("/orders"):
            return {"orders": [{"id": 11}], "total": 1}
        if path.endswith("/create"):
            return {"id": 51}
        if "/deposits/" in path:
            return {"id": 51}
        if path.endswith("/balance"):
            return {"balance": 9.9}
        return {}

    monkeypatch.setattr(module, "request_json", _fake_request_json)

    categories = module.list_bot_catalog_categories(catalog_type="full", bot_id=1)
    items = module.list_bot_catalog_items(
        category_id=3,
        country="US",
        bin_number="411111",
        page=2,
        page_size=5,
    )
    bin_row = module.get_bot_bin_info("411111")
    merchants = module.list_bot_merchants()
    merchant_items = module.list_bot_merchant_items(merchant_id=7, page=2, page_size=6)
    cart_created = module.add_bot_cart_item(user_id=8, category_id=3, quantity=2)
    cart = module.get_bot_cart(user_id=8)
    removed = module.remove_bot_cart_item(cart_item_id=31, user_id=8)
    checked_out = module.checkout_bot_order(user_id=8, bot_id=2)
    orders = module.list_bot_orders(user_id=8, page=2, page_size=10)
    deposit_created = module.create_bot_deposit(user_id=8, amount=9.9, bot_id=2)
    deposit = module.get_bot_deposit(deposit_id=51, user_id=8)
    balance = module.get_bot_balance(user_id=8)

    assert categories[0]["id"] == 1
    assert items["total"] == 1
    assert bin_row["bin_number"] == "411111"
    assert merchants[0]["id"] == 7
    assert merchant_items["total"] == 1
    assert cart_created["id"] == 31
    assert cart["total_amount"] == 0
    assert removed["ok"] is True
    assert checked_out["status"] == "completed"
    assert orders["total"] == 1
    assert deposit_created["id"] == 51
    assert deposit["id"] == 51
    assert balance["balance"] == 9.9

    assert calls[0] == {
        "method": "GET",
        "path": "/api/v1/bot/catalog/categories",
        "payload": {"type": "full", "bot_id": 1},
    }
    assert calls[1]["path"] == "/api/v1/bot/catalog/items"
    assert calls[2]["path"] == "/api/v1/bot/bin/411111"
    assert calls[3]["path"] == "/api/v1/bot/merchants"
    assert calls[4]["path"] == "/api/v1/bot/merchants/7/items"
    assert calls[5]["path"] == "/api/v1/bot/cart/items"
    assert calls[6]["path"] == "/api/v1/bot/cart"
    assert calls[7]["path"] == "/api/v1/bot/cart/items/31"
    assert calls[8]["path"] == "/api/v1/bot/orders/checkout"
    assert calls[9]["path"] == "/api/v1/bot/orders"
    assert calls[10]["path"] == "/api/v1/bot/deposits/create"
    assert calls[11]["path"] == "/api/v1/bot/deposits/51"
    assert calls[12]["path"] == "/api/v1/bot/balance"


def test_spec_parity_dispatch_alias_and_detail_routes(monkeypatch):
    module = importlib.import_module("services.reflex_api")

    monkeypatch.setattr(
        module,
        "get_bot_snapshot_service",
        lambda bot_id: {"id": bot_id, "name": "Bot Detail"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_agent_snapshot_service",
        lambda agent_id: {"id": agent_id, "name": "Agent Detail"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_merchant_snapshot_service",
        lambda merchant_id: {"id": merchant_id, "name": "Merchant Detail"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_inventory_import_task_snapshot_service",
        lambda task_id: {"id": task_id, "status": "completed"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "list_inventory_library_items_service",
        lambda inventory_id: [{"id": 1, "inventory_id": inventory_id}],
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_export_task_service",
        lambda task_type, operator_id, filters_json: {
            "id": 88,
            "type": task_type,
            "operator_id": operator_id,
            "filters_json": filters_json,
        },
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "poll_export_task_snapshot_service",
        lambda task_id: {"id": int(task_id), "status": "processing"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "resolve_export_download_payload_service",
        lambda task_id, exports_root=None: {"task_id": int(task_id), "file_name": "exp.csv"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "toggle_user_ban_service",
        lambda **kwargs: {"id": kwargs["user_id"], "status": "active"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "get_user_snapshot_service",
        lambda user_id: {"id": user_id, "status": "active"},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "adjust_user_balance_service",
        lambda **kwargs: {"id": kwargs["user_id"], "balance": 99.0},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_manual_deposit_service",
        lambda **kwargs: {"id": 66, "amount": float(kwargs["amount"])},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "approve_inventory_review_task_service",
        lambda review_id, reviewed_by: {"id": review_id, "reviewed_by": reviewed_by},
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "process_push_queue_service",
        lambda batch_size=20: {"processed": batch_size, "sent": batch_size - 1},
        raising=False,
    )

    bot_detail = module.dispatch_request("GET", "/api/v1/bots/11")
    agent_detail = module.dispatch_request("GET", "/api/v1/agents/21")
    merchant_detail = module.dispatch_request("GET", "/api/v1/merchants/31")
    task_detail = module.dispatch_request("GET", "/api/v1/inventory/import-tasks/41")
    library_items = module.dispatch_request("GET", "/api/v1/inventory/libraries/51/items")

    order_export = module.dispatch_request(
        "POST",
        "/api/v1/orders/exports",
        {"operator_id": 1, "filters_json": {"bot_name": "Main Bot"}},
    )
    user_export = module.dispatch_request(
        "POST",
        "/api/v1/users/exports",
        {"operator_id": 2, "filters_json": {"status": "active"}},
    )
    export_snapshot = module.dispatch_request("GET", "/api/v1/exports/88")
    export_download = module.dispatch_request("GET", "/api/v1/exports/88/download")

    user_status = module.dispatch_request(
        "PATCH",
        "/api/v1/users/7/status",
        {"action": "ban", "operator_username": "admin"},
    )
    user_adjust = module.dispatch_request(
        "POST",
        "/api/v1/users/7/balance-adjustments",
        {"action": "credit", "amount": "9.9", "operator_username": "admin"},
    )
    manual_deposit = module.dispatch_request(
        "POST",
        "/api/v1/finance/deposits/manual",
        {"user_identifier": "10001", "amount": "3.5", "operator_username": "admin"},
    )
    review_approved = module.dispatch_request(
        "POST",
        "/api/v1/push/reviews/3/approve",
        {"reviewed_by": "admin"},
    )
    polled = module.dispatch_request("POST", "/api/v1/push/queue/poll", {"batch_size": 9})

    assert bot_detail["name"] == "Bot Detail"
    assert agent_detail["name"] == "Agent Detail"
    assert merchant_detail["name"] == "Merchant Detail"
    assert task_detail["status"] == "completed"
    assert library_items[0]["inventory_id"] == 51
    assert order_export["type"] == "order"
    assert user_export["type"] == "user"
    assert export_snapshot["status"] == "processing"
    assert export_download["file_name"] == "exp.csv"
    assert user_status["status"] == "active"
    assert user_adjust["balance"] == 99.0
    assert manual_deposit["amount"] == 3.5
    assert review_approved["id"] == 3
    assert polled["sent"] == 8
