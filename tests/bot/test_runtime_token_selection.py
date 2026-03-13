from __future__ import annotations

import asyncio
from pathlib import Path


def test_binding_token_set_dedup_and_sort():
    import bot.runtime as module

    values = module._binding_token_set(
        [
            {"token": "b-token"},
            {"token": "a-token"},
            {"token": "b-token"},
            {"token": ""},
            {},
        ]
    )
    assert values == ("a-token", "b-token")


def test_run_polling_group_noop_on_empty_bindings():
    import bot.runtime as module

    asyncio.run(module._run_polling_group([]))


def test_build_dispatcher_is_singleton_and_reusable():
    import bot.runtime as module

    first = module._build_dispatcher()
    second = module._build_dispatcher()
    assert first is second


def test_acquire_supervisor_lock_rejects_alive_foreign_pid(tmp_path: Path, monkeypatch):
    import bot.runtime as module

    lock_file = tmp_path / "bot_supervisor.pid"
    lock_file.write_text("99999", encoding="utf-8")
    monkeypatch.setattr(module, "_LOCK_FILE", lock_file, raising=False)
    monkeypatch.setattr(module.os, "getpid", lambda: 12345, raising=True)
    monkeypatch.setattr(module, "_is_pid_alive", lambda pid: int(pid) == 99999, raising=False)

    assert module._acquire_supervisor_lock() is False


def test_acquire_supervisor_lock_accepts_stale_pid_and_writes_self(tmp_path: Path, monkeypatch):
    import bot.runtime as module

    lock_file = tmp_path / "bot_supervisor.pid"
    lock_file.write_text("88888", encoding="utf-8")
    monkeypatch.setattr(module, "_LOCK_FILE", lock_file, raising=False)
    monkeypatch.setattr(module.os, "getpid", lambda: 12345, raising=True)
    monkeypatch.setattr(module, "_is_pid_alive", lambda pid: False, raising=False)

    assert module._acquire_supervisor_lock() is True
    assert lock_file.read_text(encoding="utf-8").strip() == "12345"


def test_is_pid_alive_accepts_current_process():
    import os
    import bot.runtime as module

    assert module._is_pid_alive(os.getpid()) is True
