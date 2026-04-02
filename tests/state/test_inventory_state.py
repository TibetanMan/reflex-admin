from __future__ import annotations

import asyncio
from typing import Any

import test_reflex.state.inventory as inventory_state_module
from test_reflex.state.inventory import InventoryItem, InventoryState


class _FakeInventoryState:
    _find_inventory_item = InventoryState._find_inventory_item
    _build_preview_data = InventoryState._build_preview_data
    _decode_upload_content = InventoryState._decode_upload_content
    _reset_append_state = InventoryState._reset_append_state
    close_append_modal = InventoryState.close_append_modal.fn

    def __init__(self, *, items: list[InventoryItem]) -> None:
        self.inventory_items = items
        self.show_append_modal = False
        self.append_inventory_id = None
        self.append_name = ""
        self.append_merchant = ""
        self.append_category = ""
        self.append_unit_price = 0.0
        self.append_pick_price = 0.0
        self.append_push_ad = False
        self.append_upload_file_content = ""
        self.append_preview_data: list[dict[str, Any]] = []
        self.append_result: dict[str, int] = {}
        self.delimiter = "|"
        self.append_delimiter = "|"
        self.is_appending = False
        self.append_progress = 0
        self.load_inventory_data_called = False

    def load_inventory_data(self) -> None:
        self.load_inventory_data_called = True


class _FakeLoadInventoryState:
    _default_merchant_name = InventoryState._default_merchant_name

    def __init__(self) -> None:
        self.inventory_items = []
        self.merchant_names = []
        self.inventory_categories = []
        self.merchant_filter_options = []
        self.import_merchant = ""
        self.import_category = ""
        self.current_page = 1

    @property
    def total_pages(self) -> int:
        return 1


class _FakeUploadFile:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


def test_open_append_modal_prefills_existing_inventory_values() -> None:
    item = InventoryItem(
        id=7,
        name="US-VISA",
        category="全资库 一手",
        merchant="平台自营",
        unit_price=12.5,
        pick_price=6.5,
        status="active",
        bot_enabled=True,
        sold=1,
        remaining=4,
        total=5,
        created_at="2026-03-23 10:00:00",
    )
    state = _FakeInventoryState(items=[item])

    InventoryState.open_append_modal.fn(state, 7)

    assert state.show_append_modal is True
    assert state.append_inventory_id == 7
    assert state.append_name == "US-VISA"
    assert state.append_merchant == "平台自营"
    assert state.append_category == "全资库 一手"
    assert state.append_unit_price == 12.5
    assert state.append_pick_price == 6.5
    assert state.append_upload_file_content == ""
    assert state.append_preview_data == []


def test_append_import_submits_to_existing_inventory(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_append_inventory_library_items(**kwargs):
        captured.update(kwargs)
        return {
            "library": {"id": 7, "name": "US-VISA"},
            "result": {"total": 2, "success": 1, "duplicate": 1, "invalid": 0},
        }

    monkeypatch.setattr(
        inventory_state_module,
        "append_inventory_library_items",
        _fake_append_inventory_library_items,
    )

    item = InventoryItem(
        id=7,
        name="US-VISA",
        category="全资库 一手",
        merchant="平台自营",
        unit_price=12.5,
        pick_price=6.5,
        status="active",
        bot_enabled=True,
        sold=1,
        remaining=4,
        total=5,
        created_at="2026-03-23 10:00:00",
    )
    state = _FakeInventoryState(items=[item])
    InventoryState.open_append_modal.fn(state, 7)
    state.append_upload_file_content = "4111111111111111|12|2028|123|US"
    state.append_preview_data = [{"index": 1, "raw": "4111111111111111|12|2028|123|US"}]

    InventoryState.submit_append_import.fn(state, "alice")

    assert captured == {
        "inventory_id": 7,
        "delimiter": "|",
        "content": "4111111111111111|12|2028|123|US",
        "push_ad": False,
        "operator_username": "alice",
        "source_filename": "inventory_append.txt",
    }
    assert state.append_result == {"total": 2, "success": 1, "duplicate": 1, "invalid": 0}
    assert state.load_inventory_data_called is True
    assert state.show_append_modal is False


def test_load_inventory_data_uses_readable_all_filter(monkeypatch) -> None:
    monkeypatch.setattr(inventory_state_module, "list_inventory_snapshot", lambda: [])
    monkeypatch.setattr(
        inventory_state_module,
        "list_inventory_filter_options",
        lambda: {
            "merchant_names": ["平台自营"],
            "category_names": ["全资库 一手"],
        },
    )
    state = _FakeLoadInventoryState()

    InventoryState.load_inventory_data.fn(state)

    assert state.merchant_filter_options == ["全部", "平台自营"]


def test_handle_file_upload_accepts_gbk_encoded_text() -> None:
    state = _FakeInventoryState(items=[])
    upload = _FakeUploadFile("平台自营|商品".encode("gbk"))

    asyncio.run(InventoryState.handle_file_upload.fn(state, [upload]))

    assert state.upload_file_content == "平台自营|商品"
    assert state.preview_data[0]["fields"] == 2


def test_handle_append_file_upload_accepts_gbk_encoded_text() -> None:
    state = _FakeInventoryState(items=[])
    upload = _FakeUploadFile("平台自营|商品".encode("gbk"))

    asyncio.run(InventoryState.handle_append_file_upload.fn(state, [upload]))

    assert state.append_upload_file_content == "平台自营|商品"
    assert state.append_preview_data[0]["fields"] == 2


def test_handle_file_upload_strips_utf8_bom() -> None:
    state = _FakeInventoryState(items=[])
    upload = _FakeUploadFile("平台自营|商品".encode("utf-8-sig"))

    asyncio.run(InventoryState.handle_file_upload.fn(state, [upload]))

    assert state.upload_file_content == "平台自营|商品"
    assert not state.upload_file_content.startswith("\ufeff")
