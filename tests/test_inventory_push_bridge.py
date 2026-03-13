import test_reflex.state.inventory as inventory_module
from services.push_queue import list_review_tasks, register_inventory_review_task, reset_push_storage


def _build_import_state():
    state = inventory_module.InventoryState()
    state.upload_file_content = "4111111111111111|12/30|123\n4222222222222222|11/29|456"
    state.import_name = "新上架库存"
    state.import_merchant = "平台自营"
    state.import_category = "全资库 一手"
    state.import_unit_price = 3.5
    state.import_pick_price = 0.8
    return state


def test_successful_inventory_import_registers_review_when_push_ad_enabled(
    tmp_path, monkeypatch
):
    reset_push_storage()
    monkeypatch.setattr(inventory_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(inventory_module.InventoryState, "load_inventory_data", lambda self: None)

    def _fake_import_inventory_library(**kwargs):
        assert kwargs["push_ad"] is True
        register_inventory_review_task(
            inventory_id=101,
            inventory_name=kwargs["name"],
            merchant_name=kwargs["merchant_name"],
            source="inventory_import",
        )
        return {
            "library": {"id": 101},
            "task_id": 1,
            "result": {"total": 2, "success": 2, "duplicate": 0, "invalid": 0},
        }

    monkeypatch.setattr(
        inventory_module,
        "import_inventory_library",
        _fake_import_inventory_library,
    )

    state = _build_import_state()
    state.import_push_ad = True

    result = state.start_import()
    reviews = list_review_tasks()

    assert any(item["inventory_name"] == "新上架库存" for item in reviews)
    assert "/push" not in repr(result)


def test_successful_inventory_import_skips_review_when_push_ad_disabled(
    tmp_path, monkeypatch
):
    reset_push_storage()
    monkeypatch.setattr(inventory_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(inventory_module.InventoryState, "load_inventory_data", lambda self: None)

    def _fake_import_inventory_library(**kwargs):
        assert kwargs["push_ad"] is False
        return {
            "library": {"id": 102},
            "task_id": 2,
            "result": {"total": 2, "success": 2, "duplicate": 0, "invalid": 0},
        }

    monkeypatch.setattr(
        inventory_module,
        "import_inventory_library",
        _fake_import_inventory_library,
    )

    state = _build_import_state()
    state.import_push_ad = False

    state.start_import()
    reviews = list_review_tasks()

    assert not any(item["inventory_name"] == "新上架库存" for item in reviews)
