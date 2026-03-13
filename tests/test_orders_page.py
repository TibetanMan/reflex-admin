from test_reflex.pages.orders import export_modal, order_detail_modal, refund_modal


def test_order_detail_modal_has_accessible_title_and_description():
    rendered = repr(order_detail_modal())

    assert "RadixThemesDialog.Title" in rendered
    assert "RadixThemesDialog.Description" in rendered
    assert "handle_detail_modal_change" in rendered


def test_refund_and_export_modals_keep_dialog_a11y_structure():
    refund_rendered = repr(refund_modal())
    export_rendered = repr(export_modal())

    assert "RadixThemesDialog.Title" in refund_rendered
    assert "RadixThemesDialog.Description" in refund_rendered
    assert "RadixThemesDialog.Title" in export_rendered
    assert "RadixThemesDialog.Description" in export_rendered
