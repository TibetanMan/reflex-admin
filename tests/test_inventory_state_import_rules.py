from __future__ import annotations

import test_reflex.state.inventory as inventory_module


def test_load_inventory_data_prefers_platform_merchant_as_default(monkeypatch):
    state = inventory_module.InventoryState()

    monkeypatch.setattr(
        inventory_module,
        "list_inventory_snapshot",
        lambda: [],
    )
    monkeypatch.setattr(
        inventory_module,
        "list_inventory_filter_options",
        lambda: {
            "merchant_names": ["商家A", "平台自营", "商家B"],
            "category_names": ["全资库 一手", "全资库 二手", "裸资库", "特价库"],
        },
    )

    state.load_inventory_data()

    assert state.import_merchant == "平台自营"
    assert state.import_category == "全资库 一手"


def test_start_import_requires_unit_and_pick_price(monkeypatch):
    called = {"value": False}

    def _fake_import_inventory_library(**kwargs):
        called["value"] = True
        return {
            "library": {"id": 1},
            "task_id": 1,
            "result": {"total": 1, "success": 1, "duplicate": 0, "invalid": 0},
        }

    monkeypatch.setattr(
        inventory_module,
        "import_inventory_library",
        _fake_import_inventory_library,
    )

    state = inventory_module.InventoryState()
    state.upload_file_content = "4111111111111111|12|30|123|US"
    state.import_name = "测试库"
    state.import_merchant = "平台自营"
    state.import_category = "全资库 一手"
    state.import_unit_price = 0.0
    state.import_pick_price = 0.0

    state.start_import()

    assert called["value"] is False
    assert state.is_importing is False


def test_start_import_requires_merchant_and_category(monkeypatch):
    called = {"value": False}

    def _fake_import_inventory_library(**kwargs):
        called["value"] = True
        return {
            "library": {"id": 1},
            "task_id": 1,
            "result": {"total": 1, "success": 1, "duplicate": 0, "invalid": 0},
        }

    monkeypatch.setattr(
        inventory_module,
        "import_inventory_library",
        _fake_import_inventory_library,
    )

    state = inventory_module.InventoryState()
    state.upload_file_content = "4111111111111111|12|30|123|US"
    state.import_name = "测试库"
    state.import_merchant = ""
    state.import_category = ""
    state.import_unit_price = 3.0
    state.import_pick_price = 1.0

    state.start_import()

    assert called["value"] is False
    assert state.is_importing is False


def test_toggle_status_passes_operator_username_to_inventory_api(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_toggle_inventory_status(**kwargs):
        captured.update(kwargs)
        return {"id": int(kwargs["inventory_id"]), "status": "inactive"}

    monkeypatch.setattr(
        inventory_module,
        "toggle_inventory_status",
        _fake_toggle_inventory_status,
    )

    state = inventory_module.InventoryState()
    monkeypatch.setattr(inventory_module.InventoryState, "load_inventory_data", lambda self: None)

    state.toggle_status(88, "admin")

    assert captured == {"inventory_id": 88, "operator_username": "admin"}
