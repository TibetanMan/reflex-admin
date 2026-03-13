"""Compatibility module for bot runtime helpers.

Standalone `python -m bot.main` mode has been removed.
Bot supervisor now runs inside Reflex lifespan tasks.
"""

from __future__ import annotations

from .runtime import (
    _acquire_supervisor_lock,
    _binding_token_set,
    _build_dispatcher,
    _cancel_polling_task,
    _is_pid_alive,
    _release_supervisor_lock,
    _run_polling_group,
    _run_supervisor_loop,
    run_bot_supervisor_lifespan,
)


def _main_removed() -> None:
    raise RuntimeError(
        "Standalone bot process mode was removed. "
        "Run the Reflex app (`uv run reflex run --env dev`) to start bot runtime."
    )


if __name__ == "__main__":
    _main_removed()
