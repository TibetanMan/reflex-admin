from sqlmodel import SQLModel

import shared.models  # noqa: F401


def test_phase3_user_and_export_tables_are_registered():
    tables = SQLModel.metadata.tables

    assert "user_bot_sources" in tables
    assert "export_tasks" in tables


def test_user_bot_source_has_user_bot_unique_constraint():
    table = SQLModel.metadata.tables["user_bot_sources"]

    unique_constraints = [item for item in table.constraints if item.__class__.__name__ == "UniqueConstraint"]
    unique_column_sets = {tuple(sorted(column.name for column in item.columns)) for item in unique_constraints}
    assert ("bot_id", "user_id") in unique_column_sets


def test_export_task_has_expected_progress_columns_and_default_status():
    table = SQLModel.metadata.tables["export_tasks"]

    for column_name in ("progress", "total_records", "processed_records"):
        assert column_name in table.columns

    default_value = table.columns["status"].default.arg
    assert str(default_value) == "pending"


def test_export_task_type_default_is_order():
    table = SQLModel.metadata.tables["export_tasks"]

    default_value = table.columns["type"].default.arg
    assert str(default_value) == "order"
