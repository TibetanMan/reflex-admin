from services.push_queue import (
    reset_push_storage,
    use_in_memory_push_repository,
)
from test_reflex.state.push_state import PushState


def _build_state() -> PushState:
    state = PushState()
    state.inventory_catalog = [
        {"id": 501, "name": "测试库存-501", "merchant": "平台自营", "status": "active"},
        {"id": 502, "name": "测试库存-502", "merchant": "代理商A", "status": "active"},
    ]
    state.bot_catalog = [
        {"id": 601, "name": "测试机器人-601", "owner": "平台自营", "status": "active"},
    ]
    return state


def test_push_state_stays_empty_when_storage_has_no_records(monkeypatch):
    monkeypatch.setenv("PUSH_QUEUE_BACKEND", "memory")
    use_in_memory_push_repository()
    reset_push_storage()
    state = _build_state()

    assert state.review_tasks_display == []
    assert state.push_campaigns_display == []


def test_push_state_no_longer_exposes_demo_seed_helper():
    assert not hasattr(PushState, "_seed_demo_data_if_needed")
