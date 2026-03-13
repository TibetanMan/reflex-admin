from services.export_task import (
    create_export_task,
    poll_export_task_snapshot,
    reset_export_task_storage,
    update_export_task,
    use_in_memory_export_task_repository,
)


def test_poll_export_task_snapshot_returns_latest_task_progress():
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    task = create_export_task("order", None, {"bot_name": "Main Bot"})
    update_export_task(
        task_id=task["id"],
        status="processing",
        progress=61,
        total_records=200,
        processed_records=122,
    )

    snapshot = poll_export_task_snapshot(task["id"])

    assert snapshot is not None
    assert snapshot["id"] == task["id"]
    assert snapshot["status"] == "processing"
    assert snapshot["progress"] == 61
    assert snapshot["total_records"] == 200
    assert snapshot["processed_records"] == 122
    assert snapshot["is_terminal"] is False


def test_poll_export_task_snapshot_returns_none_for_missing_task():
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    snapshot = poll_export_task_snapshot(9999)

    assert snapshot is None

