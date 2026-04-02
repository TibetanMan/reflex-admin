from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock


def _build_message(*, user_id: int = 10001, username: str | None = "tester", first_name: str = "Alice"):
    bot = SimpleNamespace(
        token="bot-token-001",
        get_me=AsyncMock(return_value=SimpleNamespace(full_name="Bot", username="bot_account")),
    )
    message = SimpleNamespace(
        bot=bot,
        from_user=SimpleNamespace(id=user_id, username=username, first_name=first_name),
        answer=AsyncMock(),
    )
    return message


def test_cmd_start_uses_db_configured_welcome_message(monkeypatch):
    from bot.handlers import start as start_handler

    message = _build_message()
    lookup_calls: list[str] = []

    async def _fake_resolve_runtime_ids(_message):
        return 1, 2

    def _fake_lookup_runtime_bot_by_token(*, token, session_factory=None):
        lookup_calls.append(token)
        return {"id": 1, "welcome_message": "  欢迎来到定制机器人  "}

    monkeypatch.setattr(start_handler, "_resolve_runtime_ids", _fake_resolve_runtime_ids)
    monkeypatch.setattr(start_handler, "get_bot_balance", lambda **_: {"balance": "8.50"})
    monkeypatch.setattr(start_handler, "get_main_menu", lambda: "MAIN_MENU")
    monkeypatch.setattr(
        start_handler,
        "get_runtime_active_bot_by_token",
        _fake_lookup_runtime_bot_by_token,
        raising=False,
    )

    asyncio.run(start_handler.cmd_start(message))

    assert lookup_calls == ["bot-token-001"]
    message.answer.assert_awaited_once_with("  欢迎来到定制机器人  ", reply_markup="MAIN_MENU")


def test_cmd_start_falls_back_to_default_when_welcome_message_absent(monkeypatch):
    from bot.handlers import start as start_handler

    message = _build_message(user_id=20002, username=None, first_name="Bob")
    lookup_calls: list[str] = []

    async def _fake_resolve_runtime_ids(_message):
        return 1, 2

    def _fake_lookup_runtime_bot_by_token(*, token, session_factory=None):
        lookup_calls.append(token)
        return {"id": 1}

    monkeypatch.setattr(start_handler, "_resolve_runtime_ids", _fake_resolve_runtime_ids)
    monkeypatch.setattr(start_handler, "get_bot_balance", lambda **_: {"balance": 12})
    monkeypatch.setattr(start_handler, "get_main_menu", lambda: "MAIN_MENU")
    monkeypatch.setattr(
        start_handler,
        "get_runtime_active_bot_by_token",
        _fake_lookup_runtime_bot_by_token,
        raising=False,
    )

    asyncio.run(start_handler.cmd_start(message))

    assert lookup_calls == ["bot-token-001"]
    expected_default_text = (
        "欢迎你，Bob\n\n"
        "用户ID: 20002\n"
        "用户名: 未设置\n"
        "余额: 12.00 USDT\n\n"
        "请使用下方菜单浏览商品、查询卡头、充值和下单。"
    )
    message.answer.assert_awaited_once_with(expected_default_text, reply_markup="MAIN_MENU")


def test_cmd_start_falls_back_to_default_when_welcome_message_is_whitespace_only(monkeypatch):
    from bot.handlers import start as start_handler

    message = _build_message(user_id=30003, username="bob3", first_name="Bobby")
    lookup_calls: list[str] = []

    async def _fake_resolve_runtime_ids(_message):
        return 1, 2

    def _fake_lookup_runtime_bot_by_token(*, token, session_factory=None):
        lookup_calls.append(token)
        return {"id": 1, "welcome_message": " \n\t "}

    monkeypatch.setattr(start_handler, "_resolve_runtime_ids", _fake_resolve_runtime_ids)
    monkeypatch.setattr(start_handler, "get_bot_balance", lambda **_: {"balance": 9.5})
    monkeypatch.setattr(start_handler, "get_main_menu", lambda: "MAIN_MENU")
    monkeypatch.setattr(
        start_handler,
        "get_runtime_active_bot_by_token",
        _fake_lookup_runtime_bot_by_token,
        raising=False,
    )

    asyncio.run(start_handler.cmd_start(message))

    assert lookup_calls == ["bot-token-001"]
    expected_default_text = (
        "欢迎你，Bobby\n\n"
        "用户ID: 30003\n"
        "用户名: @bob3\n"
        "余额: 9.50 USDT\n\n"
        "请使用下方菜单浏览商品、查询卡头、充值和下单。"
    )
    message.answer.assert_awaited_once_with(expected_default_text, reply_markup="MAIN_MENU")
