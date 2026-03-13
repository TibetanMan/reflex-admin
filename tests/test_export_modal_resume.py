from services.export_task import (
    create_export_task,
    reset_export_task_storage,
    update_export_task,
    use_in_memory_export_task_repository,
)
from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState


def test_order_open_export_modal_restores_latest_task_snapshot(monkeypatch):
    monkeypatch.setenv("EXPORT_TASK_BACKEND", "memory")
    use_in_memory_export_task_repository()
    reset_export_task_storage()
    task = create_export_task("order", None, {})
    update_export_task(
        task["id"],
        status="completed",
        progress=100,
        total_records=88,
        processed_records=88,
        file_name="orders_latest.csv",
        file_path="uploaded_files/exports/orders_latest.csv",
    )

    state = OrderState()
    state.open_export_modal()

    assert state.show_export_modal is True
    assert state.export_task_id == str(task["id"])
    assert state.export_status == "completed"
    assert state.export_progress == 100
    assert state.export_total_records == 88
    assert state.export_processed_records == 88
    assert state.export_file_name == "orders_latest.csv"


def test_user_open_export_modal_restores_latest_task_snapshot(monkeypatch):
    monkeypatch.setenv("EXPORT_TASK_BACKEND", "memory")
    use_in_memory_export_task_repository()
    reset_export_task_storage()
    task = create_export_task("user", None, {})
    update_export_task(
        task["id"],
        status="processing",
        progress=52,
        total_records=120,
        processed_records=62,
    )

    state = UserState()
    state.open_export_modal()

    assert state.show_export_modal is True
    assert state.export_task_id == str(task["id"])
    assert state.export_status == "processing"
    assert state.export_progress == 52
    assert state.export_total_records == 120
    assert state.export_processed_records == 62
    assert state.is_exporting is True
