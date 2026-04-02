from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock


def test_register_startup_commands_includes_start_and_help() -> None:
    from bot import runtime

    bot = type("FakeBot", (), {})()
    bot.set_my_commands = AsyncMock()

    asyncio.run(runtime._register_startup_commands(bot))

    bot.set_my_commands.assert_awaited_once()
    registered_commands = bot.set_my_commands.await_args.args[0]
    command_names = {command.command for command in registered_commands}
    assert command_names == {"start", "help"}


def test_bot_runner_start_registers_commands_before_polling(monkeypatch) -> None:
    from bot import runtime

    class _FakeUpdate:
        def outer_middleware(self, _middleware) -> None:
            return None

    class _FakeDispatcher:
        def __init__(self) -> None:
            self.update = _FakeUpdate()
            self.routers: list[object] = []

        def include_router(self, router: object) -> None:
            self.routers.append(router)

        async def stop_polling(self) -> None:
            raise RuntimeError("Polling is not started")

    class _FakeSession:
        async def close(self) -> None:
            return None

    class _FakeBot:
        def __init__(self, *, token: str) -> None:
            self.token = token
            self.session = _FakeSession()

    registration_order: list[str] = []

    async def _fake_register_startup_commands(bot: object) -> None:
        assert isinstance(bot, _FakeBot)
        registration_order.append("registered")

    class _FakeTask:
        def done(self) -> bool:
            return False

    def _fake_create_task(coro, *, name: str):
        assert name == "bot-poll-demo"
        assert registration_order == ["registered"]
        coro.close()
        return _FakeTask()

    monkeypatch.setattr(runtime, "Dispatcher", _FakeDispatcher)
    monkeypatch.setattr(runtime, "Bot", _FakeBot)
    monkeypatch.setattr(runtime, "create_start_router", lambda: object())
    monkeypatch.setattr(runtime, "create_menu_router", lambda: object())
    monkeypatch.setattr(runtime, "_register_startup_commands", _fake_register_startup_commands, raising=False)
    monkeypatch.setattr(runtime.asyncio, "create_task", _fake_create_task)

    runner = runtime._BotRunner(token="token-1", name="demo")

    asyncio.run(runner.start())

    assert registration_order == ["registered"]


def test_bot_runner_start_cleans_up_when_command_registration_fails(monkeypatch) -> None:
    from bot import runtime

    class _FakeUpdate:
        def outer_middleware(self, _middleware) -> None:
            return None

    class _FakeDispatcher:
        def __init__(self) -> None:
            self.update = _FakeUpdate()
            self.routers: list[object] = []

        def include_router(self, router: object) -> None:
            self.routers.append(router)

        async def stop_polling(self) -> None:
            raise RuntimeError("Polling is not started")

    close_mock = AsyncMock()

    class _FakeSession:
        async def close(self) -> None:
            await close_mock()

    class _FakeBot:
        def __init__(self, *, token: str) -> None:
            self.token = token
            self.session = _FakeSession()

    async def _failing_register_startup_commands(_bot: object) -> None:
        raise RuntimeError("command registration failed")

    def _unexpected_create_task(_coro, *, name: str):
        raise AssertionError(f"polling task should not be created: {name}")

    monkeypatch.setattr(runtime, "Dispatcher", _FakeDispatcher)
    monkeypatch.setattr(runtime, "Bot", _FakeBot)
    monkeypatch.setattr(runtime, "create_start_router", lambda: object())
    monkeypatch.setattr(runtime, "create_menu_router", lambda: object())
    monkeypatch.setattr(runtime, "_register_startup_commands", _failing_register_startup_commands, raising=False)
    monkeypatch.setattr(runtime.asyncio, "create_task", _unexpected_create_task)

    runner = runtime._BotRunner(token="token-1", name="demo")

    try:
        asyncio.run(runner.start())
        assert False, "runner.start should raise when command registration fails"
    except RuntimeError as exc:
        assert str(exc) == "command registration failed"

    close_mock.assert_awaited_once()
    assert runner._task is None
    assert runner._bot is None
    assert runner._dp is None


def test_supervisor_loop_continues_when_runner_start_fails(monkeypatch) -> None:
    from bot import runtime

    stop_event = asyncio.Event()
    start_attempts: list[str] = []
    stop_calls: list[str] = []

    class _FakeRunner:
        def __init__(self, token: str, name: str) -> None:
            self.token = token
            self.name = name

        async def start(self) -> None:
            start_attempts.append(self.token)
            if len(start_attempts) == 1:
                raise RuntimeError("registration failed")

        async def stop(self) -> None:
            stop_calls.append(self.token)

        def check_error(self):
            return None

    async def _fake_to_thread(_func, *, preferred_token: str):
        assert preferred_token == ""
        return [{"token": "token-A", "name": "Alpha"}]

    sleep_count = 0

    async def _fake_sleep(_seconds: int) -> None:
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 2:
            stop_event.set()

    monkeypatch.setattr(runtime, "_BotRunner", _FakeRunner)
    monkeypatch.setattr(runtime.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(runtime.asyncio, "sleep", _fake_sleep)

    asyncio.run(
        runtime._run_supervisor_loop(
            preferred_token=None,
            poll_interval_seconds=1,
            stop_event=stop_event,
        )
    )

    assert start_attempts == ["token-A", "token-A"]
    assert stop_calls == ["token-A", "token-A"]
