import os

import pytest
from sqlalchemy import inspect
from sqlmodel import SQLModel, create_engine

import shared.models  # noqa: F401


DATABASE_URL = os.getenv("DATABASE_URL", "")
RUN_LIVE = os.getenv("RUN_LIVE_POSTGRES_TESTS", "") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_LIVE or not DATABASE_URL,
    reason="Set RUN_LIVE_POSTGRES_TESTS=1 and DATABASE_URL to run live PostgreSQL checks.",
)


def _engine():
    sync_url = DATABASE_URL.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


def test_live_postgres_create_all_and_required_tables():
    engine = _engine()
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    required_tables = {
        "system_settings",
        "admin_audit_logs",
        "balance_ledgers",
        "inventory_libraries",
        "inventory_import_tasks",
        "inventory_import_line_errors",
        "user_bot_sources",
        "export_tasks",
        "push_review_tasks",
    }
    assert required_tables.issubset(tables)


def test_live_postgres_numeric_precision_and_unique_constraints():
    engine = _engine()
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)

    ledger_columns = {col["name"]: col for col in inspector.get_columns("balance_ledgers")}
    for name in ("amount", "before_balance", "after_balance"):
        column_type = ledger_columns[name]["type"]
        assert getattr(column_type, "precision", None) == 18
        assert getattr(column_type, "scale", None) == 2

    library_columns = {col["name"]: col for col in inspector.get_columns("inventory_libraries")}
    for name in ("unit_price", "pick_price"):
        column_type = library_columns[name]["type"]
        assert getattr(column_type, "precision", None) == 18
        assert getattr(column_type, "scale", None) == 2

    user_bot_uniques = inspector.get_unique_constraints("user_bot_sources")
    unique_sets = {tuple(sorted(item["column_names"])) for item in user_bot_uniques}
    assert ("bot_id", "user_id") in unique_sets
