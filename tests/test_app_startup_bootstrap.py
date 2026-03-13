import inspect
from types import SimpleNamespace

import test_reflex.test_reflex as app_entry
from sqlalchemy.exc import SQLAlchemyError


def test_app_entry_registers_startup_bootstrap_hook():
    source = inspect.getsource(app_entry)

    assert "run_startup_bootstrap" in source
    assert "_bootstrap_runtime_state" in source
    assert "register_lifespan_task" in source
    assert "run_bot_supervisor_lifespan" in source
    assert "run_deposit_reconcile_lifespan" in source
    assert "ensure_managed_bot_process" not in source


def test_bootstrap_guard_swallows_sqlalchemy_errors_when_not_strict(monkeypatch):
    monkeypatch.setenv("REFLEX_STRICT_STARTUP_BOOTSTRAP", "0")

    def _raise_db_error():
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(app_entry, "run_startup_bootstrap", _raise_db_error)

    app_entry._run_startup_bootstrap_with_guard()


def test_bootstrap_guard_raises_sqlalchemy_errors_in_strict_mode(monkeypatch):
    monkeypatch.setenv("REFLEX_STRICT_STARTUP_BOOTSTRAP", "1")

    def _raise_db_error():
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(app_entry, "run_startup_bootstrap", _raise_db_error)

    try:
        app_entry._run_startup_bootstrap_with_guard()
    except SQLAlchemyError:
        return
    raise AssertionError("Expected SQLAlchemyError in strict mode.")


def test_sync_runtime_backend_env_uses_settings_values(monkeypatch):
    app_entry.os.environ.pop("EXPORT_TASK_BACKEND", None)
    app_entry.os.environ.pop("PUSH_QUEUE_BACKEND", None)

    app_entry._sync_runtime_backend_env(
        SimpleNamespace(
            export_task_backend="db",
            push_queue_backend="db",
        )
    )

    assert app_entry.os.getenv("EXPORT_TASK_BACKEND") == "db"
    assert app_entry.os.getenv("PUSH_QUEUE_BACKEND") == "db"
    app_entry.os.environ.pop("EXPORT_TASK_BACKEND", None)
    app_entry.os.environ.pop("PUSH_QUEUE_BACKEND", None)


def test_sync_runtime_backend_env_forces_db_only(monkeypatch):
    app_entry.os.environ.pop("EXPORT_TASK_BACKEND", None)
    app_entry.os.environ.pop("PUSH_QUEUE_BACKEND", None)

    app_entry._sync_runtime_backend_env(
        SimpleNamespace(
            export_task_backend="memory",
            push_queue_backend="memory",
        )
    )

    assert app_entry.os.getenv("EXPORT_TASK_BACKEND") == "db"
    assert app_entry.os.getenv("PUSH_QUEUE_BACKEND") == "db"
    app_entry.os.environ.pop("EXPORT_TASK_BACKEND", None)
    app_entry.os.environ.pop("PUSH_QUEUE_BACKEND", None)


def test_sync_runtime_backend_env_overrides_existing_memory_env(monkeypatch):
    app_entry.os.environ["EXPORT_TASK_BACKEND"] = "memory"
    app_entry.os.environ["PUSH_QUEUE_BACKEND"] = "memory"

    app_entry._sync_runtime_backend_env(
        SimpleNamespace(
            export_task_backend="memory",
            push_queue_backend="memory",
        )
    )

    assert app_entry.os.getenv("EXPORT_TASK_BACKEND") == "db"
    assert app_entry.os.getenv("PUSH_QUEUE_BACKEND") == "db"
    app_entry.os.environ.pop("EXPORT_TASK_BACKEND", None)
    app_entry.os.environ.pop("PUSH_QUEUE_BACKEND", None)
