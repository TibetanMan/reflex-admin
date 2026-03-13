import inspect

import test_reflex.test_reflex as app_entry
from test_reflex.pages.index import quick_actions


def test_dashboard_import_inventory_button_targets_inventory_modal_flow():
    rendered = repr(quick_actions())

    assert "open_import_modal_from_dashboard" in rendered
    assert "/inventory/import" not in rendered


def test_inventory_route_registers_page_load_handler_for_import_modal():
    source = inspect.getsource(app_entry)

    assert "on_load=InventoryState.handle_inventory_page_load" in source
