from __future__ import annotations

import inspect

import test_reflex.pages.table as table_page_module
from test_reflex.pages.table import TableState


def test_table_state_loads_rows_from_user_service():
    source = inspect.getsource(TableState.load_table_data.fn)
    assert "list_users_snapshot(" in source


def test_table_state_status_toggle_uses_user_service():
    source = inspect.getsource(TableState.toggle_user_status.fn)
    refresh_source = inspect.getsource(TableState.refresh_list.fn)
    assert "toggle_user_ban(" in source
    assert "load_table_data" in source
    assert "load_table_data" in refresh_source


def test_table_state_default_rows_are_empty():
    state = TableState()
    assert state.users == []


def test_table_page_registers_loader_and_has_no_static_users_seed():
    source = inspect.getsource(table_page_module.table_page)
    assert "load_table_data" in source
    assert "refresh_list" in source
    assert "user_detail_modal" in source
    assert "role_filter_options" in source
    assert not hasattr(table_page_module, "USERS_DATA")


def test_table_row_actions_bind_status_toggle():
    source = inspect.getsource(table_page_module.table_row)
    assert "open_detail_modal" in source
    assert "copy_user_identifier" in source
    assert "toggle_user_status" in source


def test_table_state_detail_and_copy_handlers_exist():
    detail_source = inspect.getsource(TableState.open_detail_modal.fn)
    copy_source = inspect.getsource(TableState.copy_user_identifier.fn)
    close_source = inspect.getsource(TableState.close_detail_modal.fn)
    assert "_find_user(" in detail_source
    assert "set_clipboard" in copy_source
    assert "show_detail_modal = False" in close_source


def test_table_state_builds_dynamic_role_filter_options():
    state = TableState()
    state.users = [
        {"id": 1, "role": "user"},
        {"id": 2, "role": "agent"},
        {"id": 3, "role": "merchant"},
        {"id": 4, "role": "agent"},
    ]
    options = state.role_filter_options
    assert options[0] == "全部角色"
    assert options.count("agent") == 1
    assert "merchant" in options
    assert "user" in options


def test_status_badge_uses_rx_cond_for_var_compatibility():
    source = inspect.getsource(table_page_module.status_badge)
    assert "rx.cond(" in source
    assert "if status ==" not in source


def test_table_page_header_actions_are_bound_to_real_handlers():
    source = inspect.getsource(table_page_module.table_page)
    assert "export_table_users_csv" in source
    assert 'rx.redirect("/users")' in source


def test_table_state_export_handler_uses_filtered_rows_and_download():
    source = inspect.getsource(TableState.export_table_users_csv.fn)
    assert "self.filtered_users" in source
    assert "rx.download(" in source
