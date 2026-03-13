from __future__ import annotations

import io
import logging
from pathlib import Path


def test_ensure_managed_bot_process_reuses_existing_pid(tmp_path: Path, monkeypatch, caplog):
    import bot.process_manager as module

    pid_file = tmp_path / "bot_supervisor.pid"
    pid_file.write_text("54321", encoding="utf-8")
    monkeypatch.setattr(module, "PID_FILE", pid_file, raising=False)
    monkeypatch.setattr(module, "_MANAGED_PROCESS", None, raising=False)
    monkeypatch.setattr(module, "_is_pid_alive", lambda pid: int(pid) == 54321, raising=False)

    def _unexpected_popen(*args, **kwargs):
        raise AssertionError("Popen should not run when managed bot process is already alive.")

    monkeypatch.setattr(module.subprocess, "Popen", _unexpected_popen, raising=True)

    with caplog.at_level(logging.INFO):
        result = module.ensure_managed_bot_process()

    assert result == 54321
    assert "already running" in caplog.text


def test_ensure_managed_bot_process_forwards_child_streams(tmp_path: Path, monkeypatch, caplog):
    import bot.process_manager as module

    pid_file = tmp_path / "bot_supervisor.pid"
    monkeypatch.setattr(module, "PID_FILE", pid_file, raising=False)
    monkeypatch.setattr(module, "_MANAGED_PROCESS", None, raising=False)
    monkeypatch.setattr(module, "_is_pid_alive", lambda pid: False, raising=False)

    captured: dict[str, object] = {}

    class _FakeProcess:
        pid = 24680
        stdout = None
        stderr = None

        def poll(self):
            return None

    def _fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess()

    registered: list[object] = []
    forwarded: list[object] = []

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen, raising=True)
    monkeypatch.setattr(module.atexit, "register", registered.append, raising=True)
    monkeypatch.setattr(module, "_start_log_forwarders", forwarded.append, raising=True)

    with caplog.at_level(logging.INFO):
        result = module.ensure_managed_bot_process()

    assert result == 24680
    assert pid_file.read_text(encoding="utf-8").strip() == "24680"
    assert captured["args"] == [module.sys.executable, "-m", "bot.main"]
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == str(module.ROOT_DIR)
    assert kwargs["env"]["BOT_MANAGED_BY_REFLEX"] == "1"
    assert kwargs["env"]["PYTHONUNBUFFERED"] == "1"
    assert kwargs["stdout"] is module.subprocess.PIPE
    assert kwargs["stderr"] is module.subprocess.PIPE
    assert kwargs["text"] is True
    assert kwargs["bufsize"] == 1
    assert forwarded and forwarded[0].pid == 24680
    assert registered == [module._terminate_managed_process]
    assert "started bot supervisor" in caplog.text.lower()


def test_pipe_stream_to_logger_writes_non_empty_lines(caplog):
    import bot.process_manager as module

    stream = io.StringIO("line-1\n\nline-2\r\n")
    with caplog.at_level(logging.INFO):
        module._pipe_stream_to_logger(stream, level=logging.INFO, prefix="bot.stdout")

    assert "[bot.stdout] line-1" in caplog.text
    assert "[bot.stdout] line-2" in caplog.text
