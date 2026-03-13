"""Process manager for auto-starting bot supervisor with Reflex."""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import IO, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]
_MANAGED_PROCESS: Optional[subprocess.Popen] = None
_ATEXIT_REGISTERED = False
logger = logging.getLogger(__name__)

_GRACEFUL_SHUTDOWN_TIMEOUT = 10  # 给 aiogram/pydantic 冷启动留足够时间


def _pipe_stream_to_logger(stream: IO[str] | None, *, level: int, prefix: str) -> None:
    if stream is None:
        return
    try:
        for raw_line in iter(stream.readline, ""):
            line = raw_line.rstrip("\r\n")
            if line:
                logger.log(level, "[%s] %s", prefix, line)
    except Exception as exc:
        # 管道破裂、stream 被关闭等情况：记录后退出，不静默消失
        logger.warning("[%s] Log forwarder exiting: %s: %s", prefix, type(exc).__name__, exc)
    finally:
        with contextlib.suppress(Exception):
            stream.close()


def _start_log_forwarders(proc: subprocess.Popen) -> None:
    stream_specs = (
        (proc.stdout, logging.INFO, "bot.stdout"),
        (proc.stderr, logging.ERROR, "bot.stderr"),
    )
    for stream, level, prefix in stream_specs:
        if stream is None:
            continue
        thread = threading.Thread(
            target=_pipe_stream_to_logger,
            kwargs={"stream": stream, "level": level, "prefix": prefix},
            name=f"bot-log-forwarder-{prefix}",
            daemon=True,
        )
        thread.start()


def _terminate_managed_process() -> None:
    global _MANAGED_PROCESS
    proc = _MANAGED_PROCESS
    if proc is None:
        return
    if proc.poll() is not None:
        _MANAGED_PROCESS = None
        return
    try:
        if os.name == "nt":
            # Windows 上 proc.terminate() 等价于 TerminateProcess()，
            # 会在子进程的 C 层触发 KeyboardInterrupt 打断 pydantic import。
            # 改用 CTRL_BREAK_EVENT，子进程可通过 signal handler 优雅退出。
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=_GRACEFUL_SHUTDOWN_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.warning("Bot supervisor did not exit in time, killing.")
        with contextlib.suppress(Exception):
            proc.kill()
    except Exception as exc:
        logger.warning("Error while terminating bot supervisor: %s", exc)
        with contextlib.suppress(Exception):
            proc.kill()
    finally:
        _MANAGED_PROCESS = None


def ensure_managed_bot_process() -> Optional[int]:
    """Ensure one bot supervisor process is running, return its pid."""
    global _MANAGED_PROCESS, _ATEXIT_REGISTERED

    if os.getenv("REFLEX_DISABLE_BOT_AUTOSTART", "0") == "1":
        logger.info("Bot supervisor autostart disabled by REFLEX_DISABLE_BOT_AUTOSTART=1.")
        return None

    # 已有托管进程且仍在运行，直接返回
    if _MANAGED_PROCESS is not None:
        if _MANAGED_PROCESS.poll() is None:
            logger.info("Bot supervisor already running with pid=%s.", _MANAGED_PROCESS.pid)
            return _MANAGED_PROCESS.pid
        # 进程已退出，清理引用
        _MANAGED_PROCESS = None

    creationflags = 0
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP 让子进程独立接收 CTRL_BREAK_EVENT
        creationflags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

    env = os.environ.copy()
    env["BOT_MANAGED_BY_REFLEX"] = "1"
    env.setdefault("PYTHONUNBUFFERED", "1")

    proc = subprocess.Popen(
        [sys.executable, "-m", "bot.main"],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )
    _start_log_forwarders(proc)
    _MANAGED_PROCESS = proc

    # 防止 Reflex 热重载时重复注册
    if not _ATEXIT_REGISTERED:
        atexit.register(_terminate_managed_process)
        _ATEXIT_REGISTERED = True

    logger.info("Started bot supervisor managed by Reflex with pid=%s.", proc.pid)
    return proc.pid