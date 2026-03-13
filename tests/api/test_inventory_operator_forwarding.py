from __future__ import annotations

import importlib


def test_inventory_api_client_update_price_passes_operator(monkeypatch):
    module = importlib.import_module("services.inventory_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"id": 1, "unit_price": 6.6, "pick_price": 2.2}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    row = module.update_inventory_price(
        inventory_id=1,
        unit_price=6.6,
        pick_price=2.2,
        operator_username="admin",
    )

    assert row["unit_price"] == 6.6
    assert captured == {
        "method": "PATCH",
        "path": "/api/v1/inventory/libraries/1/price",
        "payload": {"unit_price": 6.6, "pick_price": 2.2, "operator_username": "admin"},
    }


def test_inventory_api_client_delete_passes_operator(monkeypatch):
    module = importlib.import_module("services.inventory_api")
    captured: dict[str, object] = {}

    def _fake_request_json(method: str, path: str, payload: dict | None = None):
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr(module, "request_json", _fake_request_json)
    module.delete_inventory_library(inventory_id=8, operator_username="admin")

    assert captured == {
        "method": "DELETE",
        "path": "/api/v1/inventory/libraries/8",
        "payload": {"operator_username": "admin"},
    }


def test_inventory_price_dispatch_routes_operator_to_service(monkeypatch):
    module = importlib.import_module("services.reflex_api")
    captured: dict[str, object] = {}

    def _fake_update_inventory_price_service(**kwargs):
        captured.update(kwargs)
        return {"id": int(kwargs["inventory_id"]), "unit_price": kwargs["unit_price"]}

    monkeypatch.setattr(module, "update_inventory_price_service", _fake_update_inventory_price_service)
    row = module.dispatch_request(
        "PATCH",
        "/api/v1/inventory/libraries/3/price",
        {"unit_price": 7.7, "pick_price": 1.1, "operator_username": "admin"},
    )

    assert row["id"] == 3
    assert captured == {
        "inventory_id": 3,
        "unit_price": 7.7,
        "pick_price": 1.1,
        "operator_username": "admin",
    }


def test_inventory_delete_dispatch_routes_operator_to_service(monkeypatch):
    module = importlib.import_module("services.reflex_api")
    captured: dict[str, object] = {}

    def _fake_delete_inventory_library_service(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(module, "delete_inventory_library_service", _fake_delete_inventory_library_service)
    row = module.dispatch_request(
        "DELETE",
        "/api/v1/inventory/libraries/5",
        {"operator_username": "admin"},
    )

    assert row["ok"] is True
    assert captured == {"inventory_id": 5, "operator_username": "admin"}
