from sqlalchemy import Numeric
from sqlmodel import SQLModel

import shared.models  # noqa: F401


def _assert_numeric_18_2(table_name: str, column_names: tuple[str, ...]) -> None:
    table = SQLModel.metadata.tables[table_name]
    for column_name in column_names:
        column = table.columns[column_name]
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 18
        assert column.type.scale == 2


def _assert_fk_target(table_name: str, column_name: str, target_fullname: str) -> None:
    table = SQLModel.metadata.tables[table_name]
    targets = {fk.target_fullname for fk in table.columns[column_name].foreign_keys}
    assert target_fullname in targets


def _index_names(table_name: str) -> set[str]:
    table = SQLModel.metadata.tables[table_name]
    return {index.name for index in table.indexes}


def test_amount_columns_use_numeric_18_2():
    money_columns = {
        "users": ("balance", "total_deposit", "total_spent"),
        "agents": ("balance", "total_profit", "frozen_balance"),
        "merchants": ("balance", "total_sales", "frozen_balance"),
        "categories": ("base_price", "min_price"),
        "cart_items": ("unit_price", "subtotal"),
        "bot_instances": ("total_revenue",),
        "orders": ("total_amount", "paid_amount", "platform_profit", "agent_profit", "supplier_profit"),
        "order_items": ("unit_price", "subtotal"),
        "deposits": ("amount", "actual_amount"),
        "wallet_addresses": ("balance", "total_received"),
        "product_items": ("cost_price", "selling_price", "sold_price"),
    }
    for table_name, column_names in money_columns.items():
        _assert_numeric_18_2(table_name, column_names)


def test_spec_recommended_foreign_keys_are_present():
    # Spec 4.3 recommended these to become FK columns.
    _assert_fk_target("orders", "bot_id", "bot_instances.id")
    _assert_fk_target("deposits", "bot_id", "bot_instances.id")
    _assert_fk_target("wallet_addresses", "bot_id", "bot_instances.id")

    # Additional sales relation constraints added in this optimization pass.
    _assert_fk_target("wallet_addresses", "agent_id", "agents.id")
    _assert_fk_target("product_items", "sold_to_user_id", "users.id")
    _assert_fk_target("product_items", "sold_to_bot_id", "bot_instances.id")


def test_high_frequency_composite_indexes_are_present():
    assert {
        "ix_orders_status_created_at",
        "ix_orders_bot_status_created_at",
        "ix_orders_user_created_at",
    }.issubset(_index_names("orders"))

    assert {
        "ix_deposits_status_created_at",
        "ix_deposits_bot_status_created_at",
        "ix_deposits_user_created_at",
    }.issubset(_index_names("deposits"))

    assert {
        "ix_product_items_status_category_supplier_created",
    }.issubset(_index_names("product_items"))

    assert {
        "ix_push_message_tasks_status_created_at",
        "ix_push_message_tasks_status_scheduled_at",
    }.issubset(_index_names("push_message_tasks"))
