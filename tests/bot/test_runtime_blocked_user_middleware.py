from __future__ import annotations

import asyncio

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage


def _forbidden_error(description: str) -> TelegramForbiddenError:
    return TelegramForbiddenError(
        method=SendMessage(chat_id=1, text="hello"),
        message=description,
    )


def test_blocked_user_forbidden_error_is_ignored():
    import bot.runtime as module

    middleware = module._IgnoreBlockedUserForbiddenMiddleware()

    async def _handler(_event, _data):
        raise _forbidden_error("Telegram server says - Forbidden: bot was blocked by the user")

    result = asyncio.run(middleware.__call__(_handler, object(), {}))
    assert result is None


def test_other_forbidden_error_is_raised():
    import bot.runtime as module

    middleware = module._IgnoreBlockedUserForbiddenMiddleware()

    async def _handler(_event, _data):
        raise _forbidden_error("Telegram server says - Forbidden: bot can't initiate conversation with a user")

    with pytest.raises(TelegramForbiddenError):
        asyncio.run(middleware.__call__(_handler, object(), {}))
