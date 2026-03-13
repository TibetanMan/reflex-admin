from __future__ import annotations

import asyncio


def test_run_deposit_reconcile_lifespan_starts_loop_and_releases_lock(monkeypatch):
    import services.deposit_reconcile_runtime as module

    lifecycle: dict[str, object] = {"released": 0, "started": False}

    monkeypatch.setattr(module, "_is_reconcile_enabled", lambda: True, raising=True)
    monkeypatch.setattr(module, "_acquire_reconcile_lock", lambda: True, raising=True)

    def _release() -> None:
        lifecycle["released"] = int(lifecycle["released"]) + 1

    monkeypatch.setattr(module, "_release_reconcile_lock", _release, raising=True)

    async def _fake_loop(*, poll_interval_seconds, batch_limit, stop_event):
        lifecycle["started"] = True
        lifecycle["interval"] = poll_interval_seconds
        lifecycle["limit"] = batch_limit
        await stop_event.wait()

    monkeypatch.setattr(module, "_run_deposit_reconcile_loop", _fake_loop, raising=True)

    async def _run() -> None:
        async with module.run_deposit_reconcile_lifespan(
            poll_interval_seconds=7,
            batch_limit=19,
        ):
            await asyncio.sleep(0)

    asyncio.run(_run())

    assert lifecycle["started"] is True
    assert lifecycle["interval"] == 7
    assert lifecycle["limit"] == 19
    assert lifecycle["released"] == 1


def test_run_deposit_reconcile_lifespan_skips_when_disabled(monkeypatch):
    import services.deposit_reconcile_runtime as module

    called = {"loop": False, "released": False, "lock": False}

    monkeypatch.setattr(module, "_is_reconcile_enabled", lambda: False, raising=True)

    def _acquire() -> bool:
        called["lock"] = True
        return True

    monkeypatch.setattr(module, "_acquire_reconcile_lock", _acquire, raising=True)

    def _release() -> None:
        called["released"] = True

    monkeypatch.setattr(module, "_release_reconcile_lock", _release, raising=True)

    async def _fake_loop(*, poll_interval_seconds, batch_limit, stop_event):
        del poll_interval_seconds, batch_limit
        called["loop"] = True
        await stop_event.wait()

    monkeypatch.setattr(module, "_run_deposit_reconcile_loop", _fake_loop, raising=True)

    async def _run() -> None:
        async with module.run_deposit_reconcile_lifespan():
            await asyncio.sleep(0)

    asyncio.run(_run())

    assert called["lock"] is False
    assert called["loop"] is False
    assert called["released"] is False
