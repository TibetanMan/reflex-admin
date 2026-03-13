from test_reflex.state.inventory import InventoryState


def test_open_import_modal_from_dashboard_sets_pending_flag_and_redirects():
    state = InventoryState()

    result = state.open_import_modal_from_dashboard()

    assert state.open_import_modal_on_load is True
    assert "/inventory" in repr(result)


def test_handle_inventory_page_load_opens_modal_when_queued():
    state = InventoryState()
    state.open_import_modal_on_load = True
    state.show_import_modal = False

    state.handle_inventory_page_load()

    assert state.show_import_modal is True
    assert state.open_import_modal_on_load is False
