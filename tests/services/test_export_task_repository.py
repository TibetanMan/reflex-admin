from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import shared.models  # noqa: F401
from services.export_task import InMemoryExportTaskRepository, SqlModelExportTaskRepository


def _sqlite_session_factory(tmp_path: Path):
    db_file = tmp_path / "export_task_repo.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _factory() -> Session:
        return Session(engine)

    return _factory


def test_in_memory_repository_create_and_update_task():
    repository = InMemoryExportTaskRepository()

    created = repository.create_task(
        task_type="order",
        operator_id=None,
        filters_json='{"bot_name":"Main Bot"}',
    )
    assert created["id"] == 1
    assert created["type"] == "order"
    assert created["status"] == "pending"
    assert created["progress"] == 0

    updated = repository.update_task(
        task_id=created["id"],
        status="processing",
        progress=45,
        total_records=200,
        processed_records=90,
    )
    assert updated is not None
    assert updated["status"] == "processing"
    assert updated["progress"] == 45
    assert updated["total_records"] == 200
    assert updated["processed_records"] == 90


def test_sqlmodel_repository_create_and_update_task(tmp_path: Path):
    repository = SqlModelExportTaskRepository(session_factory=_sqlite_session_factory(tmp_path))

    created = repository.create_task(
        task_type="user",
        operator_id=9,
        filters_json='{"bot_name":"All Bots"}',
    )
    assert created["id"] > 0
    assert created["type"] == "user"
    assert created["status"] == "pending"

    updated = repository.update_task(
        task_id=created["id"],
        status="completed",
        progress=100,
        total_records=30,
        processed_records=30,
        file_name="users_all.csv",
        file_path="uploaded_files/exports/users_all.csv",
    )
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["progress"] == 100
    assert updated["file_name"] == "users_all.csv"

