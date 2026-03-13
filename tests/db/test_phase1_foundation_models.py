from sqlalchemy import Numeric
from sqlmodel import SQLModel

import shared.models  # noqa: F401


def test_phase1_foundation_tables_are_registered():
    tables = SQLModel.metadata.tables

    assert "system_settings" in tables
    assert "admin_audit_logs" in tables
    assert "balance_ledgers" in tables


def test_balance_ledger_amount_columns_use_numeric_18_2():
    table = SQLModel.metadata.tables["balance_ledgers"]

    for column_name in ("amount", "before_balance", "after_balance"):
        column = table.columns[column_name]
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 18
        assert column.type.scale == 2


def test_system_setting_key_is_unique():
    table = SQLModel.metadata.tables["system_settings"]

    assert table.columns["key"].unique is True


def test_balance_ledger_request_id_is_unique():
    table = SQLModel.metadata.tables["balance_ledgers"]

    assert table.columns["request_id"].unique is True
