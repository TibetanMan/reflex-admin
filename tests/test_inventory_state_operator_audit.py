from __future__ import annotations

import test_reflex.state.inventory as inventory_module


def test_update_price_passes_operator_username_to_inventory_api(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_update_inventory_price(**kwargs):
        captured.update(kwargs)
        return {"id": int(kwargs["inventory_id"]), "unit_price": 9.9, "pick_price": 3.3}

    monkeypatch.setattr(inventory_module, "update_inventory_price", _fake_update_inventory_price)
    monkeypatch.setattr(inventory_module.InventoryState, "load_inventory_data", lambda self: None)
    monkeypatch.setattr(inventory_module.InventoryState, "close_price_modal", lambda self: None)

    state = inventory_module.InventoryState()
    state.selected_item_id = 77
    state.edit_unit_price = 9.9
    state.edit_pick_price = 3.3

    state.update_price("admin")

    assert captured == {
        "inventory_id": 77,
        "unit_price": 9.9,
        "pick_price": 3.3,
        "operator_username": "admin",
    }


def test_delete_item_passes_operator_username_to_inventory_api(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_delete_inventory_library(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(inventory_module, "delete_inventory_library", _fake_delete_inventory_library)
    monkeypatch.setattr(inventory_module.InventoryState, "load_inventory_data", lambda self: None)
    monkeypatch.setattr(inventory_module.InventoryState, "close_delete_modal", lambda self: None)

    state = inventory_module.InventoryState()
    state.selected_item_id = 66

    state.delete_item("admin")

    assert captured == {"inventory_id": 66, "operator_username": "admin"}
