import inspect

from test_reflex.state.push_state import PushState


def test_sync_linked_sources_bootstraps_push_repository_from_env():
    source = inspect.getsource(PushState.sync_linked_sources.fn)

    assert "ensure_push_repository_from_env(" in source
    assert "list_inventory_snapshot(" in source
    assert "list_bots_snapshot(" in source
    assert "get_state(" not in source
    assert "_seed_demo_data_if_needed(" not in source
