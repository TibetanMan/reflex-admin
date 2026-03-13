from __future__ import annotations

from sqlmodel import SQLModel

import shared.models  # noqa: F401


def test_inventory_library_has_bot_enabled_flag():
    table = SQLModel.metadata.tables["inventory_libraries"]
    assert "is_bot_enabled" in table.columns


def test_order_item_has_purchase_snapshot_fields():
    table = SQLModel.metadata.tables["order_items"]
    assert "purchase_mode" in table.columns
    assert "purchase_filter_json" in table.columns
