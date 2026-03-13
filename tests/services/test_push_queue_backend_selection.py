from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import shared.models  # noqa: F401
import services.push_queue as push_queue_module
from services.push_queue import (
    ensure_push_repository_from_env,
    get_push_queue_backend_name,
    use_in_memory_push_repository,
)


def _sqlite_session_factory(tmp_path: Path):
    db_file = tmp_path / "backend_switch.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _factory() -> Session:
        return Session(engine)

    return _factory


def test_backend_selection_defaults_to_db(monkeypatch):
    monkeypatch.delenv("PUSH_QUEUE_BACKEND", raising=False)
    use_in_memory_push_repository()

    backend = ensure_push_repository_from_env()

    assert backend == "db"
    assert get_push_queue_backend_name() == "db"


def test_backend_selection_switches_to_db_when_configured(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PUSH_QUEUE_BACKEND", "db")
    use_in_memory_push_repository()

    backend = ensure_push_repository_from_env(
        session_factory=_sqlite_session_factory(tmp_path)
    )

    assert backend == "db"
    assert get_push_queue_backend_name() == "db"


def test_push_backend_memory_env_is_blocked_outside_test_mode(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PUSH_QUEUE_BACKEND", "memory")
    monkeypatch.setattr(push_queue_module, "_memory_backend_allowed", lambda: False)
    use_in_memory_push_repository()

    backend = ensure_push_repository_from_env(
        session_factory=_sqlite_session_factory(tmp_path)
    )

    assert backend == "db"
    assert get_push_queue_backend_name() == "db"
