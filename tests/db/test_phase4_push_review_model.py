from sqlmodel import SQLModel

import shared.models  # noqa: F401


def test_phase4_push_review_table_is_registered():
    tables = SQLModel.metadata.tables
    assert "push_review_tasks" in tables


def test_push_review_task_status_default_is_pending_review():
    table = SQLModel.metadata.tables["push_review_tasks"]
    default_value = table.columns["status"].default.arg
    assert str(default_value) == "pending_review"


def test_push_review_task_foreign_keys_exist():
    table = SQLModel.metadata.tables["push_review_tasks"]

    assert "inventory_library_id" in table.columns
    assert "merchant_id" in table.columns
    assert "reviewed_by" in table.columns
    assert len(table.columns["inventory_library_id"].foreign_keys) == 1
    assert len(table.columns["merchant_id"].foreign_keys) == 1
