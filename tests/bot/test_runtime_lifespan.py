from __future__ import annotations

import asyncio


def test_run_bot_supervisor_lifespan_starts_loop_and_releases_lock(monkeypatch):
    import bot.runtime as module

    lifecycle: dict[str, object] = {"released": 0, "started": False}

    monkeypatch.setattr(module, "_acquire_supervisor_lock", lambda: True, raising=True)

    def _release() -> None:
        lifecycle["released"] = int(lifecycle["released"]) + 1

    monkeypatch.setattr(module, "_release_supervisor_lock", _release, raising=True)

    async def _fake_loop(*, preferred_token, poll_interval_seconds, stop_event):
        lifecycle["started"] = True
        lifecycle["token"] = preferred_token
        lifecycle["interval"] = poll_interval_seconds
        await stop_event.wait()

    monkeypatch.setattr(module, "_run_supervisor_loop", _fake_loop, raising=True)

    async def _run() -> None:
        async with module.run_bot_supervisor_lifespan(
            preferred_token="abc-token",
            poll_interval_seconds=1,
        ):
            await asyncio.sleep(0)

    asyncio.run(_run())

    assert lifecycle["started"] is True
    assert lifecycle["token"] == "abc-token"
    assert lifecycle["interval"] == 1
    assert lifecycle["released"] == 1


def test_run_bot_supervisor_lifespan_skips_when_lock_denied(monkeypatch):
    import bot.runtime as module

    called = {"loop": False, "released": False}

    monkeypatch.setattr(module, "_acquire_supervisor_lock", lambda: False, raising=True)

    def _release() -> None:
        called["released"] = True

    monkeypatch.setattr(module, "_release_supervisor_lock", _release, raising=True)

    async def _fake_loop(*, preferred_token, poll_interval_seconds, stop_event):
        called["loop"] = True
        await stop_event.wait()

    monkeypatch.setattr(module, "_run_supervisor_loop", _fake_loop, raising=True)

    async def _run() -> None:
        async with module.run_bot_supervisor_lifespan(preferred_token="abc-token"):
            await asyncio.sleep(0)

    asyncio.run(_run())

    assert called["loop"] is False
    assert called["released"] is False
