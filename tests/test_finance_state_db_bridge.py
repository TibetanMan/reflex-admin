import inspect

import test_reflex.pages.finance as finance_page_module
from test_reflex.state.finance_state import FinanceState


def test_finance_state_loads_from_finance_service():
    source = inspect.getsource(FinanceState.load_finance_data.fn)

    assert "list_finance_deposits(" in source
    assert "list_finance_wallets(" in source


def test_finance_state_manual_deposit_calls_finance_service():
    source = inspect.getsource(FinanceState.process_manual_deposit.fn)

    assert "create_manual_deposit(" in source


def test_finance_state_manual_deposit_surfaces_service_error(monkeypatch):
    import test_reflex.state.finance_state as finance_state_module

    def _raise_wallet_error(**kwargs):
        del kwargs
        raise ValueError("Current bot has no configured receiving wallet.")

    monkeypatch.setattr(finance_state_module, "create_manual_deposit", _raise_wallet_error)

    state = FinanceState()
    state.manual_user_id = "123456789"
    state.manual_amount = "10.00"
    state.manual_remark = "manual"

    event = state.process_manual_deposit(operator_username="admin")
    assert "wallet" in str(event).lower()


def test_finance_state_onchain_sync_calls_finance_service():
    source = inspect.getsource(FinanceState.sync_onchain_deposits.fn)

    assert "reconcile_finance_deposits(" in source


def test_finance_state_export_uses_filtered_rows_and_download():
    source = inspect.getsource(FinanceState.export_finance_report_csv.fn)

    assert "self.filtered_deposits" in source
    assert "rx.download(" in source


def test_finance_page_registers_on_mount_loader():
    source = inspect.getsource(finance_page_module.finance_page)

    assert "load_finance_data" in source


def test_finance_page_export_button_is_bound():
    source = inspect.getsource(finance_page_module.finance_page)

    assert "export_finance_report_csv" in source


def test_finance_deposit_row_actions_are_bound():
    source = inspect.getsource(finance_page_module.render_deposit_record_row)

    assert "copy_deposit_no" in source
    assert "open_tx_hash_link" in source


def test_finance_state_row_action_handlers_exist():
    copy_source = inspect.getsource(FinanceState.copy_deposit_no.fn)
    tx_source = inspect.getsource(FinanceState.open_tx_hash_link.fn)

    assert "set_clipboard" in copy_source
    assert "call_script" in tx_source
