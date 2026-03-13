import inspect

from test_reflex.state.merchant_state import MerchantState


def test_export_merchant_orders_reads_order_snapshot_service():
    source = inspect.getsource(MerchantState.export_merchant_orders.fn)

    assert "list_orders_snapshot(" in source
    assert "await self.get_state(" not in source
