import inspect

from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState


def test_order_state_poll_method_uses_export_task_poll_snapshot():
    source = inspect.getsource(OrderState.poll_export_task_status.fn)

    assert "poll_export_task_snapshot(" in source
    assert "list_export_tasks(" in source


def test_user_state_poll_method_uses_export_task_poll_snapshot():
    source = inspect.getsource(UserState.poll_export_task_status.fn)

    assert "poll_export_task_snapshot(" in source
    assert "list_export_tasks(" in source

