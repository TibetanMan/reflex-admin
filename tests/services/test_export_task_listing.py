from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import shared.models  # noqa: F401
from services.export_task import (
    create_export_task,
    list_export_tasks,
    reset_export_task_storage,
    update_export_task,
    use_in_memory_export_task_repository,
    use_database_export_task_repository,
)


def _sqlite_session_factory(tmp_path: Path):
    db_file = tmp_path / "export_task_listing.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _factory() -> Session:
        return Session(engine)

    return _factory


def test_list_export_tasks_returns_latest_first_for_memory_backend():
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    first = create_export_task("order", None, {"k": 1})
    second = create_export_task("user", None, {"k": 2})
    third = create_export_task("order", None, {"k": 3})
    update_export_task(third["id"], status="completed", progress=100)

    rows = list_export_tasks(limit=10)

    assert [row["id"] for row in rows] == [third["id"], second["id"], first["id"]]


def test_list_export_tasks_supports_type_filter():
    use_in_memory_export_task_repository()
    reset_export_task_storage()

    create_export_task("order", None, {})
    create_export_task("user", None, {})
    last_order = create_export_task("order", None, {})

    rows = list_export_tasks(task_type="order", limit=10)

    assert len(rows) == 2
    assert rows[0]["id"] == last_order["id"]
    assert all(item["type"] == "order" for item in rows)


def test_list_export_tasks_works_for_db_backend(tmp_path: Path):
    use_database_export_task_repository(session_factory=_sqlite_session_factory(tmp_path))
    reset_export_task_storage()

    create_export_task("order", None, {})
    latest = create_export_task("user", 1, {})

    rows = list_export_tasks(limit=5)

    assert len(rows) == 2
    assert rows[0]["id"] == latest["id"]

