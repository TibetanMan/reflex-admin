import inspect

from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState


def test_order_state_download_uses_export_task_resolution():
    source = inspect.getsource(OrderState.download_export_file.fn)

    assert "resolve_export_download_payload(" in source


def test_user_state_download_uses_export_task_resolution():
    source = inspect.getsource(UserState.download_export_file.fn)

    assert "resolve_export_download_payload(" in source

