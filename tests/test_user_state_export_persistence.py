import inspect

from test_reflex.state.user_state import UserState


def test_export_users_persists_export_task_lifecycle():
    source = inspect.getsource(UserState.export_users.fn)

    assert "ensure_export_task_repository_from_env(" in source
    assert "create_export_task(" in source
    assert "update_export_task(" in source

