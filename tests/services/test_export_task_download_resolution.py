from pathlib import Path

from services.export_task import (
    create_export_task,
    resolve_export_download_payload,
    reset_export_task_storage,
    update_export_task,
    use_in_memory_export_task_repository,
)


def test_resolve_export_download_payload_returns_valid_file(tmp_path: Path):
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    exports_root = tmp_path / "exports"
    exports_root.mkdir(parents=True, exist_ok=True)
    file_path = exports_root / "orders_demo.csv"
    file_path.write_text("order_no,amount\nORD001,10\n", encoding="utf-8")

    task = create_export_task(
        task_type="order",
        operator_id=None,
        filters_json={"bot_name": "Main Bot"},
    )
    update_export_task(
        task_id=task["id"],
        status="completed",
        progress=100,
        total_records=1,
        processed_records=1,
        file_name=file_path.name,
        file_path=str(file_path),
    )

    payload = resolve_export_download_payload(task["id"], exports_root=exports_root)

    assert payload is not None
    assert payload["file_name"] == file_path.name
    assert Path(payload["file_path"]).resolve() == file_path.resolve()


def test_resolve_export_download_payload_rejects_path_outside_exports_root(tmp_path: Path):
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    exports_root = tmp_path / "exports"
    exports_root.mkdir(parents=True, exist_ok=True)
    outside_path = tmp_path / "outside.csv"
    outside_path.write_text("a,b\n1,2\n", encoding="utf-8")

    task = create_export_task(
        task_type="user",
        operator_id=None,
        filters_json={},
    )
    update_export_task(
        task_id=task["id"],
        status="completed",
        progress=100,
        total_records=1,
        processed_records=1,
        file_name=outside_path.name,
        file_path=str(outside_path),
    )

    payload = resolve_export_download_payload(task["id"], exports_root=exports_root)

    assert payload is None


def test_resolve_export_download_payload_rejects_missing_file(tmp_path: Path):
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    exports_root = tmp_path / "exports"
    exports_root.mkdir(parents=True, exist_ok=True)
    missing = exports_root / "missing.csv"

    task = create_export_task(
        task_type="order",
        operator_id=None,
        filters_json={},
    )
    update_export_task(
        task_id=task["id"],
        status="completed",
        progress=100,
        total_records=1,
        processed_records=1,
        file_name=missing.name,
        file_path=str(missing),
    )

    payload = resolve_export_download_payload(task["id"], exports_root=exports_root)

    assert payload is None

