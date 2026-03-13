from test_reflex.pages.merchants import (
    merchant_create_modal,
    merchant_edit_modal,
    merchant_list_table,
    merchants_page,
)


def test_merchants_table_renders_from_state_not_static_rows():
    component = merchant_list_table()
    rendered = repr(component)

    assert "filtered_merchants" in rendered
    assert "toggle_merchant_status" in rendered
    assert "toggle_merchant_featured" in rendered


def test_merchants_page_has_super_admin_gate():
    component = merchants_page()
    rendered = repr(component)

    assert "is_super_admin" in rendered
    assert "shield-alert" in rendered


def test_merchants_modals_wire_open_change_and_submit_handlers():
    create_rendered = repr(merchant_create_modal())
    edit_rendered = repr(merchant_edit_modal())

    assert "handle_create_modal_change" in create_rendered
    assert "save_new_merchant" in create_rendered
    assert "handle_edit_modal_change" in edit_rendered
    assert "save_edit_merchant" in edit_rendered


def test_merchants_table_has_export_action_and_slimmed_metrics():
    rendered = repr(merchant_list_table())

    assert "export_merchant_orders" in rendered
    assert "rating" not in rendered
    assert "balance" not in rendered
