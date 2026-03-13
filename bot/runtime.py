"""Bot runtime supervisor integrated with Reflex lifespan.

Each enabled bot runs in its own independent polling loop with its own
Dispatcher instance (created via router factories), so starting / stopping
one bot never affects others.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import threading
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import TelegramObject

from services.bot_service import list_runtime_bot_bindings
from shared.config import settings
from .handlers import create_start_router, create_menu_router


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
_LOCK_FILE = ROOT_DIR / ".states" / "bot_supervisor.pid"
_LOCK_GUARD = threading.Lock()
_RESTART_COOLDOWN = 10  # seconds to wait before restarting after polling failure


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def _is_blocked_user_forbidden(exc: TelegramForbiddenError) -> bool:
    detail = str(exc).strip().lower()
    return "bot was blocked by the user" in detail


class _IgnoreBlockedUserForbiddenMiddleware(BaseMiddleware):
    """Ignore Telegram blocked-user errors so polling logs are not spammed."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramForbiddenError as exc:
            if not _is_blocked_user_forbidden(exc):
                raise
            logger.info("Ignored Telegram blocked-user error: %s", exc)
            return None


# ---------------------------------------------------------------------------
# PID lock helpers
# ---------------------------------------------------------------------------

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
        logger.warning("Failed to read bot supervisor lock file: %s", _LOCK_FILE)
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _write_lock_pid(pid: int) -> None:
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(str(int(pid)), encoding="utf-8")


def _acquire_supervisor_lock(force: bool = False) -> bool:
    current_pid = int(os.getpid())
    with _LOCK_GUARD:
        existing_pid = _read_lock_pid()
        if existing_pid > 0 and existing_pid != current_pid and _is_pid_alive(existing_pid):
            if force:
                logger.warning(
                    "Force acquiring supervisor lock, terminating old process pid=%s.",
                    existing_pid,
                )
                try:
                    os.kill(existing_pid, 9)
                except OSError:
                    pass
            else:
                logger.info("Detected existing bot supervisor process pid=%s, skip duplicate runtime.", existing_pid)
                return False
        _write_lock_pid(current_pid)
        return True


def _release_supervisor_lock() -> None:
    with _LOCK_GUARD:
        existing_pid = _read_lock_pid()
        if existing_pid and existing_pid != int(os.getpid()):
            return
        with contextlib.suppress(FileNotFoundError):
            _LOCK_FILE.unlink()


# ---------------------------------------------------------------------------
# Per-bot polling runner
# ---------------------------------------------------------------------------

class _BotRunner:
    """Manages a single bot's independent polling lifecycle.

    Each runner creates its own Dispatcher with fresh Router instances
    (via factory functions) so there is no shared state between runners.
    """

    def __init__(self, token: str, name: str) -> None:
        self.token = token
        self.name = name
        self._dp: Dispatcher | None = None
        self._bot: Bot | None = None
        self._task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start polling for this bot in a background task."""
        if self.running:
            return
        # Each bot gets its own Dispatcher with fresh router instances
        self._dp = Dispatcher()
        self._dp.update.outer_middleware(_IgnoreBlockedUserForbiddenMiddleware())
        self._dp.include_router(create_start_router())
        self._dp.include_router(create_menu_router())
        self._bot = Bot(token=self.token)
        self._task = asyncio.create_task(
            self._poll_loop(),
            name=f"bot-poll-{self.name}",
        )
        logger.info("Bot [%s] 轮询已启动。", self.name)

    async def stop(self) -> None:
        """Gracefully stop polling for this bot."""
        logger.info("Bot [%s] 正在停止...", self.name)
        # Signal aiogram to stop its internal polling loop
        if self._dp is not None:
            try:
                await self._dp.stop_polling()
            except RuntimeError:
                # "Polling is not started" — task already finished
                pass
        # Wait for the task to finish
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(self._task, timeout=35)
            if not self._task.done():
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
            self._task = None
        # Close bot HTTP session
        if self._bot is not None:
            with contextlib.suppress(Exception):
                await self._bot.session.close()
            self._bot = None
        self._dp = None
        logger.info("Bot [%s] 已停止。", self.name)

    def check_error(self) -> Exception | None:
        """Return the exception if the polling task died, else None."""
        if self._task is None or not self._task.done():
            return None
        try:
            return self._task.exception()
        except asyncio.CancelledError:
            return None

    async def _poll_loop(self) -> None:
        """Run dispatcher polling for this single bot."""
        assert self._dp is not None and self._bot is not None
        logger.info("Bot [%s] 开始接收消息。", self.name)
        await self._dp.start_polling(self._bot, handle_signals=False)
        logger.info("Bot [%s] 停止接收消息。", self.name)


# ---------------------------------------------------------------------------
# Supervisor loop
# ---------------------------------------------------------------------------

def _desired_token_map(bindings: list[dict[str, Any]]) -> dict[str, str]:
    """Return {token: name} mapping for all valid bindings."""
    result: dict[str, str] = {}
    for row in bindings:
        token = str(row.get("token") or "").strip()
        if token and token not in result:
            result[token] = str(row.get("name") or "-")
    return result


async def _run_supervisor_loop(
    *,
    preferred_token: str | None,
    poll_interval_seconds: int = 3,
    stop_event: asyncio.Event | None = None,
) -> None:
    runners: dict[str, _BotRunner] = {}  # token -> runner
    event = stop_event or asyncio.Event()

    try:
        while not event.is_set():
            # 1. Fetch desired bot set from DB
            try:
                desired_bindings = await asyncio.to_thread(
                    list_runtime_bot_bindings,
                    preferred_token=str(preferred_token or "").strip(),
                )
            except Exception:
                logger.exception("读取运行中 Bot 配置失败，%s 秒后重试。", poll_interval_seconds)
                await asyncio.sleep(poll_interval_seconds)
                continue

            desired = _desired_token_map(list(desired_bindings))

            # 2. Stop bots that are no longer in the desired set
            tokens_to_remove = [t for t in runners if t not in desired]
            for token in tokens_to_remove:
                runner = runners.pop(token)
                await runner.stop()

            # 3. Start bots that are newly in the desired set
            for token, name in desired.items():
                if token not in runners:
                    runner = _BotRunner(token=token, name=name)
                    await runner.start()
                    runners[token] = runner

            # 4. Check for crashed runners — clean up and let next iteration restart
            for token in list(runners):
                runner = runners[token]
                exc = runner.check_error()
                if exc is not None:
                    logger.error(
                        "Bot [%s] 轮询异常退出，%s 秒后自动重启: %s",
                        runner.name, _RESTART_COOLDOWN, exc,
                    )
                    await runner.stop()
                    del runners[token]
                    await asyncio.sleep(_RESTART_COOLDOWN)

            await asyncio.sleep(poll_interval_seconds)
    except asyncio.CancelledError:
        logger.info("Bot supervisor 收到停止信号，正在关闭所有 Bot...")
    finally:
        for runner in runners.values():
            await runner.stop()
        runners.clear()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _ensure_bot_logging() -> None:
    """Ensure bot-related loggers output to stderr so logs are visible in the Reflex console."""
    bot_logger = logging.getLogger("bot")
    if not bot_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
        bot_logger.addHandler(handler)
    if bot_logger.level == logging.NOTSET:
        bot_logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Reflex lifespan entry point
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def run_bot_supervisor_lifespan(
    *,
    preferred_token: str | None = None,
    poll_interval_seconds: int = 3,
) -> AsyncIterator[None]:
    _ensure_bot_logging()

    if preferred_token is None:
        preferred_token = str(getattr(settings, "bot_token", "") or "").strip()

    if not _acquire_supervisor_lock():
        yield
        return

    stop_event = asyncio.Event()
    task = asyncio.create_task(
        _run_supervisor_loop(
            preferred_token=preferred_token,
            poll_interval_seconds=poll_interval_seconds,
            stop_event=stop_event,
        ),
        name="bot-supervisor-lifespan",
    )
    try:
        logger.info("Bot 监督器启动中（Reflex lifespan 模式）...")
        yield
    finally:
        stop_event.set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        _release_supervisor_lock()
        logger.info("Bot 监督器已关闭。")
