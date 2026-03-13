import inspect

from test_reflex.state.order_state import OrderState


def test_export_orders_creates_export_task_record():
    source = inspect.getsource(OrderState.export_orders.fn)

    assert "ensure_export_task_repository_from_env(" in source
    assert "create_export_task(" in source


def test_run_export_task_updates_export_task_record():
    source = inspect.getsource(OrderState.run_export_task.fn)

    assert "update_export_task(" in source
    assert "build_export_rows_from_orders(" in source
    assert "iter_mock_order_chunks(" not in source
    assert "estimate_mock_total_records(" not in source
