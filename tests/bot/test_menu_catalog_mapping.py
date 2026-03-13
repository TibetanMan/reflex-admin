from __future__ import annotations


def test_filter_rows_for_full_basic_special_menu():
    from bot.handlers.menu import _category_rows_for_menu

    rows = [
        {"id": 1, "name": "全资库 一手", "code": "inventory_full_first_hand", "stock_count": 10},
        {"id": 2, "name": "全资库 二手", "code": "inventory_full_second_hand", "stock_count": 20},
        {"id": 3, "name": "裸资库", "code": "inventory_raw_capital", "stock_count": 30},
        {"id": 4, "name": "特价库", "code": "inventory_special_offer", "stock_count": 40},
    ]

    full_rows = _category_rows_for_menu(rows, catalog_type="full")
    basic_rows = _category_rows_for_menu(rows, catalog_type="basic")
    special_rows = _category_rows_for_menu(rows, catalog_type="special")

    assert [int(row["id"]) for row in full_rows] == [1, 2]
    assert [int(row["id"]) for row in basic_rows] == [3]
    assert [int(row["id"]) for row in special_rows] == [4]


def test_filter_rows_for_full_menu_accepts_name_fallback():
    from bot.handlers.menu import _category_rows_for_menu

    rows = [
        {"id": 1, "name": "全资库 一手", "stock_count": 10},
        {"id": 2, "name": "全资库 二手", "stock_count": 20},
        {"id": 3, "name": "裸资库", "stock_count": 30},
    ]
    full_rows = _category_rows_for_menu(rows, catalog_type="full")
    assert [int(row["id"]) for row in full_rows] == [1, 2]


def test_full_menu_rows_use_one_hand_and_two_hand_labels():
    from bot.handlers.menu import _category_rows_for_menu

    rows = _category_rows_for_menu(
        [
            {"id": 1, "name": "全资库 一手", "code": "inventory_full_first_hand"},
            {"id": 2, "name": "全资库 二手", "code": "inventory_full_second_hand"},
        ],
        catalog_type="full",
    )
    assert rows[0]["menu_label"] == "一手"
    assert rows[1]["menu_label"] == "二手"


def test_pick_direct_category_row_for_basic_and_special():
    from bot.handlers.menu import _pick_direct_category_row

    rows = [
        {"id": 1, "name": "全资库 一手", "code": "inventory_full_first_hand", "stock_count": 10},
        {"id": 2, "name": "全资库 二手", "code": "inventory_full_second_hand", "stock_count": 20},
        {"id": 3, "name": "裸资库", "code": "inventory_raw_capital", "stock_count": 30},
        {"id": 4, "name": "特价库", "code": "inventory_special_offer", "stock_count": 40},
    ]

    basic_row = _pick_direct_category_row(rows, catalog_type="basic")
    special_row = _pick_direct_category_row(rows, catalog_type="special")
    full_row = _pick_direct_category_row(rows, catalog_type="full")

    assert basic_row is not None
    assert int(basic_row["id"]) == 3
    assert special_row is not None
    assert int(special_row["id"]) == 4
    assert full_row is None


def test_library_menu_title_can_use_category_stock_total():
    from bot.handlers.menu import _library_menu_title

    rows = [
        {"name": "库A", "remaining_count": 12},
        {"name": "库B", "remaining_count": 8},
    ]
    text_with_internal_total = _library_menu_title(category_name="特价库", rows=rows)
    text_with_category_total = _library_menu_title(category_name="特价库", rows=rows, display_total=100)

    assert text_with_internal_total == "特价库-【20】\n请选择库存库："
    assert text_with_category_total == "特价库-【100】\n请选择库存库："


def test_format_head_remaining_text_numbers_only():
    from bot.handlers.menu import _format_head_remaining_text

    single = _format_head_remaining_text(["414718"], {"414718": 30})
    multi = _format_head_remaining_text(["414718", "515012"], {"414718": 30, "515012": 7})

    assert single == "30"
    assert multi == "30，7"


def test_category_display_count_prefers_library_count():
    from bot.handlers.menu import _category_display_count

    row_with_library_count = {"stock_count": 100, "library_count": 1}
    row_without_library_count = {"stock_count": 9}

    assert _category_display_count(row_with_library_count) == 1
    assert _category_display_count(row_without_library_count) == 9
