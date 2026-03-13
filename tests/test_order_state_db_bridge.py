import inspect

import test_reflex.pages.orders as orders_page_module
import test_reflex.state.order_state as order_state_module
from test_reflex.state.order_state import OrderState


def test_order_state_loads_and_mutates_via_order_service():
    load_source = inspect.getsource(OrderState.load_orders_data.fn)
    refund_source = inspect.getsource(OrderState.process_refund.fn)
    refresh_source = inspect.getsource(OrderState.refresh_list.fn)

    assert "list_orders_snapshot(" in load_source
    assert "refund_order(" in refund_source
    assert "load_orders_data" in refresh_source


def test_order_state_load_orders_data_maps_snapshot_to_order_models(monkeypatch):
    state = OrderState()

    def _fake_list_orders_snapshot():
        return [
            {
                "id": 10,
                "order_no": "ORD-FAKE-001",
                "user": "Demo (@demo)",
                "user_id": 2,
                "telegram_id": "998877",
                "bot": "Main Bot",
                "bot_id": 1,
                "items": [
                    {
                        "name": "US VISA",
                        "category": "US VISA",
                        "merchant": "Merchant One",
                        "quantity": 1,
                        "unit_price": 9.9,
                        "subtotal": 9.9,
                    }
                ],
                "item_count": 1,
                "amount": 9.9,
                "status": "completed",
                "created_at": "2026-03-06 12:00",
                "completed_at": "2026-03-06 12:05",
                "refund_reason": None,
            }
        ]

    monkeypatch.setattr(order_state_module, "list_orders_snapshot", _fake_list_orders_snapshot)

    state.load_orders_data()

    assert len(state.orders) == 1
    assert state.orders[0].order_no == "ORD-FAKE-001"
    assert state.orders[0].items[0].merchant == "Merchant One"
    assert state.available_bots[0]["name"] == "Main Bot"


def test_orders_page_registers_on_mount_loader():
    source = inspect.getsource(orders_page_module.orders_page)

    assert "load_orders_data" in source
