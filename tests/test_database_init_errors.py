from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

import shared.database as database_module


def test_init_db_wraps_operational_error_with_actionable_message(monkeypatch):
    def _raise_operational_error(*_args, **_kwargs):
        raise OperationalError("CREATE TABLE", {}, Exception("permission denied"))

    monkeypatch.setattr(
        database_module.SQLModel.metadata,
        "create_all",
        _raise_operational_error,
    )

    with pytest.raises(RuntimeError) as exc_info:
        database_module.init_db()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "127.0.0.1" in message
    assert "localhost" in message
