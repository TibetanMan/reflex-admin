from __future__ import annotations

import inspect

import test_reflex.pages.finance as finance_page_module
import test_reflex.pages.inventory as inventory_page_module
import test_reflex.pages.orders as orders_page_module
import test_reflex.pages.push as push_page_module
import test_reflex.pages.table as table_page_module
import test_reflex.pages.users as users_page_module
from test_reflex.pages.table import TableState
from test_reflex.state.finance_state import FinanceState
from test_reflex.state.inventory import InventoryState
from test_reflex.state.order_state import OrderState
from test_reflex.state.push_state import PushState
from test_reflex.state.user_state import UserState


def test_users_page_key_actions_are_bound():
    source = inspect.getsource(users_page_module.users_page)
    assert "open_export_modal" in source
    assert "refresh_list" in source
    assert "load_users_data" in source


def test_users_state_key_actions_have_side_effects():
    toggle_source = inspect.getsource(UserState.toggle_ban.fn)
    balance_source = inspect.getsource(UserState.confirm_balance_adjustment.fn)
    export_source = inspect.getsource(UserState.export_users.fn)

    assert "toggle_user_ban(" in toggle_source
    assert "adjust_user_balance(" in balance_source
    assert "create_export_task(" in export_source
    assert "update_export_task(" in export_source


def test_orders_page_key_actions_are_bound():
    page_source = inspect.getsource(orders_page_module.orders_page)
    row_source = inspect.getsource(orders_page_module.action_buttons)
    export_source = inspect.getsource(orders_page_module.export_modal)

    assert "open_export_modal" in page_source
    assert "refresh_list" in inspect.getsource(orders_page_module.filter_section)
    assert "open_detail_modal" in row_source
    assert "open_refund_modal" in row_source
    assert "process_refund" in inspect.getsource(orders_page_module.refund_modal)
    assert "export_orders" in export_source


def test_orders_state_key_actions_have_side_effects():
    refund_source = inspect.getsource(OrderState.process_refund.fn)
    export_source = inspect.getsource(OrderState.export_orders.fn)
    run_export_source = inspect.getsource(OrderState.run_export_task.fn)

    assert "refund_order(" in refund_source
    assert "create_export_task(" in export_source
    assert "build_export_rows_from_orders(" in run_export_source
    assert "update_export_task(" in run_export_source


def test_inventory_page_key_actions_are_bound():
    source = inspect.getsource(inventory_page_module.inventory_page)
    filter_source = inspect.getsource(inventory_page_module.filter_section)
    import_source = inspect.getsource(inventory_page_module.import_modal)
    price_source = inspect.getsource(inventory_page_module.price_edit_modal)
    delete_source = inspect.getsource(inventory_page_module.delete_confirm_modal)

    assert "load_inventory_data" in source
    assert "open_import_modal" in filter_source
    assert "start_import" in import_source
    assert "update_price" in price_source
    assert "delete_item" in delete_source


def test_inventory_state_key_actions_have_side_effects():
    import_source = inspect.getsource(InventoryState.start_import.fn)
    price_source = inspect.getsource(InventoryState.update_price.fn)
    delete_source = inspect.getsource(InventoryState.delete_item.fn)
    status_source = inspect.getsource(InventoryState.toggle_status.fn)

    assert "import_inventory_library(" in import_source
    assert "update_inventory_price(" in price_source
    assert "delete_inventory_library(" in delete_source
    assert "toggle_inventory_status(" in status_source


def test_finance_and_table_exports_have_download_side_effects():
    finance_export_source = inspect.getsource(FinanceState.export_finance_report_csv.fn)
    table_export_source = inspect.getsource(TableState.export_table_users_csv.fn)
    finance_page_source = inspect.getsource(finance_page_module.finance_page)
    table_page_source = inspect.getsource(table_page_module.table_page)

    assert "rx.download(" in finance_export_source
    assert "rx.download(" in table_export_source
    assert "export_finance_report_csv" in finance_page_source
    assert "export_table_users_csv" in table_page_source


def test_finance_row_handlers_have_copy_and_link_side_effects():
    row_source = inspect.getsource(finance_page_module.render_deposit_record_row)
    copy_source = inspect.getsource(FinanceState.copy_deposit_no.fn)
    link_source = inspect.getsource(FinanceState.open_tx_hash_link.fn)

    assert "copy_deposit_no" in row_source
    assert "open_tx_hash_link" in row_source
    assert "set_clipboard" in copy_source
    assert "call_script" in link_source


def test_push_page_key_actions_are_bound_and_effective():
    page_source = inspect.getsource(push_page_module.push_page)
    review_source = inspect.getsource(push_page_module.render_review_row)
    compose_source = inspect.getsource(push_page_module.push_compose_panel)
    approve_source = inspect.getsource(PushState.approve_review_and_fill_form.fn)
    queue_source = inspect.getsource(PushState.queue_push_campaign.fn)

    assert "poll_push_dashboard" in page_source
    assert "refresh_push_dashboard" in page_source
    assert "approve_review_and_fill_form" in review_source
    assert "queue_push_campaign" in compose_source
    assert "approve_inventory_review_task(" in approve_source
    assert "enqueue_push_campaign(" in queue_source
    assert "process_push_queue(" in queue_source
