from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import shared.models  # noqa: F401
import services.export_task as export_task_module
from services.export_task import (
    create_export_task,
    ensure_export_task_repository_from_env,
    get_export_task,
    get_export_task_backend_name,
    use_in_memory_export_task_repository,
)


def _sqlite_session_factory(tmp_path: Path):
    db_file = tmp_path / "export_task_backend.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _factory() -> Session:
        return Session(engine)

    return _factory


def test_export_task_backend_defaults_to_db(monkeypatch):
    monkeypatch.delenv("EXPORT_TASK_BACKEND", raising=False)
    use_in_memory_export_task_repository()

    backend = ensure_export_task_repository_from_env()

    assert backend == "db"
    assert get_export_task_backend_name() == "db"


def test_export_task_backend_switches_to_db_when_configured(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EXPORT_TASK_BACKEND", "db")
    use_in_memory_export_task_repository()

    backend = ensure_export_task_repository_from_env(
        session_factory=_sqlite_session_factory(tmp_path)
    )

    created = create_export_task(
        task_type="order",
        operator_id=None,
        filters_json='{"date_from":"2026-01-01","date_to":"2026-01-31"}',
    )
    read_back = get_export_task(created["id"])

    assert backend == "db"
    assert get_export_task_backend_name() == "db"
    assert read_back is not None
    assert read_back["id"] == created["id"]


def test_export_task_memory_env_is_blocked_outside_test_mode(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EXPORT_TASK_BACKEND", "memory")
    monkeypatch.setattr(export_task_module, "_memory_backend_allowed", lambda: False)
    use_in_memory_export_task_repository()

    backend = ensure_export_task_repository_from_env(
        session_factory=_sqlite_session_factory(tmp_path)
    )

    assert backend == "db"
    assert get_export_task_backend_name() == "db"
