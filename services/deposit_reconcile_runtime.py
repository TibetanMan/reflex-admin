"""Background runtime task for automatic on-chain deposit reconciliation."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import threading
from pathlib import Path
from typing import AsyncIterator

from services.deposit_chain_service import sync_pending_usdt_deposits


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
_LOCK_FILE = ROOT_DIR / ".states" / "deposit_reconcile.pid"
_LOCK_GUARD = threading.Lock()


def _is_pid_alive(pid: int) -> bool:
    value = int(pid or 0)
    if value <= 0:
        return False
    try:
        os.kill(value, 0)
    except OSError:
        return False
    return True


def _read_lock_pid() -> int:
    try:
        text = _LOCK_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return 0
    except Exception:
        logger.warning("Failed to read deposit reconcile lock file: %s", _LOCK_FILE)
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _write_lock_pid(pid: int) -> None:
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(str(int(pid)), encoding="utf-8")


def _acquire_reconcile_lock() -> bool:
    current_pid = int(os.getpid())
    with _LOCK_GUARD:
        existing_pid = _read_lock_pid()
        if existing_pid > 0 and existing_pid != current_pid and _is_pid_alive(existing_pid):
            logger.info(
                "Detected existing deposit reconcile process pid=%s, skip duplicate runtime.",
                existing_pid,
            )
            return False
        _write_lock_pid(current_pid)
        return True


def _release_reconcile_lock() -> None:
    with _LOCK_GUARD:
        existing_pid = _read_lock_pid()
        if existing_pid and existing_pid != int(os.getpid()):
            return
        with contextlib.suppress(FileNotFoundError):
            _LOCK_FILE.unlink()


def _reconcile_interval_seconds() -> int:
    try:
        raw = int(os.getenv("REFLEX_DEPOSIT_RECONCILE_INTERVAL_SECONDS", "20"))
    except ValueError:
        raw = 20
    return max(5, min(raw, 3600))


def _reconcile_batch_limit() -> int:
    try:
        raw = int(os.getenv("REFLEX_DEPOSIT_RECONCILE_LIMIT", "200"))
    except ValueError:
        raw = 200
    return max(1, min(raw, 1000))


def _is_reconcile_enabled() -> bool:
    return str(os.getenv("REFLEX_ENABLE_DEPOSIT_RECONCILE", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


async def _run_deposit_reconcile_loop(
    *,
    poll_interval_seconds: int,
    batch_limit: int,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            summary = await asyncio.to_thread(sync_pending_usdt_deposits, limit=batch_limit)
            updated = int(summary.get("updated") or 0)
            if updated > 0:
                logger.info(
                    "Deposit reconcile updated=%s completed=%s confirming=%s failed=%s expired=%s",
                    updated,
                    int(summary.get("completed") or 0),
                    int(summary.get("confirming") or 0),
                    int(summary.get("failed") or 0),
                    int(summary.get("expired") or 0),
                )
        except Exception:
            logger.exception("Deposit reconcile loop failed.")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except asyncio.TimeoutError:
            continue


@contextlib.asynccontextmanager
async def run_deposit_reconcile_lifespan(
    *,
    poll_interval_seconds: int | None = None,
    batch_limit: int | None = None,
) -> AsyncIterator[None]:
    """Run background auto-reconcile task in Reflex lifespan."""
    if not _is_reconcile_enabled():
        logger.info("Deposit reconcile runtime disabled by env.")
        yield
        return

    if not _acquire_reconcile_lock():
        yield
        return

    interval = poll_interval_seconds or _reconcile_interval_seconds()
    limit = batch_limit or _reconcile_batch_limit()
    stop_event = asyncio.Event()
    task = asyncio.create_task(
        _run_deposit_reconcile_loop(
            poll_interval_seconds=interval,
            batch_limit=limit,
            stop_event=stop_event,
        ),
        name="deposit-reconcile-lifespan",
    )

    try:
        logger.info(
            "Deposit reconcile runtime started (interval=%ss, limit=%s).",
            interval,
            limit,
        )
        yield
    finally:
        stop_event.set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        _release_reconcile_lock()
        logger.info("Deposit reconcile runtime stopped.")
