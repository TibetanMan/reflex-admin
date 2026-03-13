import reflex as rx

from test_reflex.pages.finance import (
    deposit_list_table,
    finance_page,
    manual_deposit_modal,
    wallet_list,
)


def test_finance_deposit_table_renders_from_state_data():
    component = deposit_list_table()
    rendered = repr(component)

    assert "filtered_deposits" in rendered
    assert "DEP20240208001" not in rendered


def test_finance_wallet_list_renders_from_state_data():
    component = wallet_list()
    rendered = repr(component)

    assert "wallets" in rendered
    assert "TXyz123...abc456" not in rendered


def test_manual_deposit_modal_syncs_open_state_and_cancel_close():
    component = manual_deposit_modal()
    rendered = repr(component)

    assert "handle_manual_deposit_modal_change" in rendered
    assert "close_manual_deposit_modal" in rendered


def test_finance_page_refresh_button_wires_to_state_event():
    component = finance_page()
    rendered = repr(component)

    assert "refresh_list" in rendered
    assert "sync_onchain_deposits" in rendered
