from __future__ import annotations

import inspect
import importlib

import test_reflex.pages.finance as finance_page_module
import test_reflex.pages.inventory as inventory_page_module
import test_reflex.pages.orders as orders_page_module
import test_reflex.pages.table as table_page_module
import test_reflex.pages.users as users_page_module
from test_reflex.state.finance_state import FinanceState
from test_reflex.state.inventory import InventoryState
from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState
from test_reflex.pages.table import TableState

settings_page_module = importlib.import_module("test_reflex.pages.settings")


def test_pages_bind_operator_username_from_auth_state():
    finance_source = inspect.getsource(finance_page_module.manual_deposit_modal)
    inventory_source = inspect.getsource(inventory_page_module.import_modal)
    refund_source = inspect.getsource(orders_page_module.refund_modal)
    user_actions_source = inspect.getsource(users_page_module.user_actions)
    user_balance_source = inspect.getsource(users_page_module.balance_confirm_modal)
    table_source = inspect.getsource(table_page_module.table_row)
    settings_usdt_source = inspect.getsource(settings_page_module.usdt_query_api_section)
    settings_bins_source = inspect.getsource(settings_page_module.bins_query_api_section)
    settings_tg_source = inspect.getsource(settings_page_module.telegram_push_section)
    settings_confirm_source = inspect.getsource(settings_page_module.default_usdt_confirm_modal)

    assert "AuthState.username" in finance_source
    assert "AuthState.username" in inventory_source
    assert "AuthState.username" in refund_source
    assert "AuthState.username" in user_actions_source
    assert "AuthState.username" in user_balance_source
    assert "AuthState.username" in table_source
    settings_combined = (
        settings_usdt_source
        + settings_bins_source
        + settings_tg_source
        + settings_confirm_source
    )
    assert settings_combined.count("AuthState.username") >= 4


def test_state_write_actions_do_not_hardcode_admin_operator_username():
    finance_source = inspect.getsource(FinanceState.process_manual_deposit.fn)
    inventory_source = inspect.getsource(InventoryState.start_import.fn)
    refund_source = inspect.getsource(OrderState.process_refund.fn)
    user_toggle_source = inspect.getsource(UserState.toggle_ban.fn)
    user_balance_source = inspect.getsource(UserState.confirm_balance_adjustment.fn)
    table_toggle_source = inspect.getsource(TableState.toggle_user_status.fn)
    settings_save_default_source = inspect.getsource(
        settings_page_module.SettingsState.confirm_default_usdt_address_change.fn
    )
    settings_save_usdt_source = inspect.getsource(
        settings_page_module.SettingsState.save_usdt_query_api_settings.fn
    )
    settings_save_bins_source = inspect.getsource(
        settings_page_module.SettingsState.save_bins_query_api_settings.fn
    )
    settings_save_tg_source = inspect.getsource(
        settings_page_module.SettingsState.save_telegram_push_settings.fn
    )

    for source in (
        finance_source,
        inventory_source,
        refund_source,
        user_toggle_source,
        user_balance_source,
        table_toggle_source,
        settings_save_default_source,
        settings_save_usdt_source,
        settings_save_bins_source,
        settings_save_tg_source,
    ):
        assert 'operator_username="admin"' not in source
        assert "operator_username_value" in source
