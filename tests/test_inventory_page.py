from test_reflex.pages import inventory as inventory_page


def test_inventory_upload_accept_uses_mime_to_extension_mapping():
    accept = inventory_page.INVENTORY_UPLOAD_ACCEPT

    assert accept["text/plain"] == [".txt"]
    assert accept["text/csv"] == [".csv"]
    assert ".txt" not in accept
    assert ".csv" not in accept
