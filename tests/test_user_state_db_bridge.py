import inspect

import test_reflex.pages.users as users_page_module
from test_reflex.state.user_state import UserState


def test_user_state_uses_user_service_for_db_bridge():
    load_source = inspect.getsource(UserState.load_users_data.fn)
    ban_source = inspect.getsource(UserState.toggle_ban.fn)
    adjust_source = inspect.getsource(UserState.confirm_balance_adjustment.fn)
    refresh_source = inspect.getsource(UserState.refresh_list.fn)

    assert "list_users_snapshot(" in load_source
    assert "toggle_user_ban(" in ban_source
    assert "adjust_user_balance(" in adjust_source
    assert "load_users_data" in refresh_source


def test_users_page_registers_on_mount_loader():
    source = inspect.getsource(users_page_module.users_page)

    assert "load_users_data" in source
