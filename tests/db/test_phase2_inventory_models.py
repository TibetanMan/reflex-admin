from sqlalchemy import Numeric
from sqlmodel import SQLModel

import shared.models  # noqa: F401


def test_phase2_inventory_tables_are_registered():
    tables = SQLModel.metadata.tables

    assert "inventory_libraries" in tables
    assert "inventory_import_tasks" in tables
    assert "inventory_import_line_errors" in tables


def test_inventory_library_prices_use_numeric_18_2():
    table = SQLModel.metadata.tables["inventory_libraries"]

    for column_name in ("unit_price", "pick_price"):
        column = table.columns[column_name]
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 18
        assert column.type.scale == 2


def test_inventory_import_task_status_has_expected_default():
    table = SQLModel.metadata.tables["inventory_import_tasks"]

    default_value = table.columns["status"].default.arg
    assert str(default_value) == "pending"


def test_product_item_has_inventory_library_fk_column():
    table = SQLModel.metadata.tables["product_items"]

    assert "inventory_library_id" in table.columns
    assert len(table.columns["inventory_library_id"].foreign_keys) == 1
