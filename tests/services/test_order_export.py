from datetime import date, datetime
import services.order_export as order_export_module

from services.order_export import (
    ExportParams,
    build_export_rows_from_orders,
    build_export_filename,
    validate_export_params,
)


def test_validate_export_params_success():
    params = validate_export_params(
        bot_name="Main Bot",
        date_from="2026-01-01",
        date_to="2026-01-31",
    )

    assert params == ExportParams(
        bot_name="Main Bot",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )


def test_validate_export_params_raises_for_invalid_range():
    try:
        validate_export_params(
            bot_name="Main Bot",
            date_from="2026-02-01",
            date_to="2026-01-01",
        )
    except ValueError as exc:
        assert "date_to" in str(exc)
    else:
        raise AssertionError("expected ValueError for reversed date range")


def test_build_export_filename_sanitizes_bot_name():
    name = build_export_filename(
        bot_name="Main/Bot #1",
        now=datetime(2026, 2, 8, 18, 30, 0),
    )

    assert name.startswith("orders_main_bot_1_20260208_183000")
    assert name.endswith(".csv")


def test_build_export_rows_from_orders_filters_by_bot_and_date_range():
    params = ExportParams(
        bot_name="Main Bot",
        date_from=date(2026, 1, 10),
        date_to=date(2026, 1, 20),
    )
    rows = [
        {
            "order_no": "ORD-001",
            "bot": "Main Bot",
            "user": "alice",
            "telegram_id": "1001",
            "item_count": 2,
            "amount": 12.5,
            "status": "completed",
            "created_at": "2026-01-15 08:00:00",
        },
        {
            "order_no": "ORD-002",
            "bot": "Other Bot",
            "user": "bob",
            "telegram_id": "1002",
            "item_count": 1,
            "amount": 9.9,
            "status": "pending",
            "created_at": "2026-01-15 09:00:00",
        },
        {
            "order_no": "ORD-003",
            "bot": "Main Bot",
            "user": "carol",
            "telegram_id": "1003",
            "item_count": 1,
            "amount": 5.0,
            "status": "completed",
            "created_at": "2026-01-25 09:00:00",
        },
    ]

    export_rows = build_export_rows_from_orders(rows=rows, params=params)

    assert len(export_rows) == 1
    assert export_rows[0]["order_no"] == "ORD-001"
    assert export_rows[0]["bot_name"] == "Main Bot"
    assert export_rows[0]["username"] == "alice"


def test_order_export_module_has_no_mock_streaming_helpers():
    assert not hasattr(order_export_module, "estimate_mock_total_records")
    assert not hasattr(order_export_module, "iter_mock_order_chunks")
