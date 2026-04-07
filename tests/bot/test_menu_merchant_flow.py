import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.handlers import menu


def test_library_action_keyboard_uses_unit_price_for_random_button():
    markup = menu._library_action_keyboard(
        {
            "library_id": 7,
            "pick_price": 10.0,
            "unit_price": 20.0,
            "prefix_counts": {"3C": 0, "3D": 0, "4C": 0, "4D": 0, "5C": 0, "5D": 0, "6C": 0, "6D": 0},
        }
    )

    first_row = markup.inline_keyboard[0]
    assert first_row[0].text == "🎯 挑头购买 10.00U"
    assert first_row[1].text == "🎲 随机购买 20.00U"


def test_handle_merchant_items_renders_library_buttons_with_lib_callbacks(monkeypatch):
    async def fake_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    def fake_list_bot_merchant_items(*, merchant_id, page, page_size):
        del merchant_id, page, page_size
        return {
            "merchant_name": "Merchant One",
            "page": 1,
            "total_pages": 1,
            "items": [
                {
                    "id": 7,
                    "name": "Merchant Library",
                    "remaining_count": 3,
                }
            ],
        }

    monkeypatch.setattr(menu.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(menu, "list_bot_merchant_items", fake_list_bot_merchant_items)

    callback = SimpleNamespace(
        data="MER:5:1",
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )

    asyncio.run(menu.handle_merchant_items(callback))

    sent_text = callback.message.edit_text.await_args.args[0]
    markup = callback.message.edit_text.await_args.kwargs["reply_markup"]

    assert "Merchant One" in sent_text
    assert "请选择库存库" in sent_text
    assert markup is not None
    assert markup.inline_keyboard[0][0].text == "Merchant Library【3】"
    assert markup.inline_keyboard[0][0].callback_data == "LIB:7"


def test_handle_library_action_random_prompt_uses_unit_price(monkeypatch):
    async def fake_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    def fake_get_bot_library_snapshot(*, library_id):
        del library_id
        return {
            "library_id": 7,
            "library_name": "Merchant Library",
            "pick_price": 10.0,
            "unit_price": 20.0,
        }

    monkeypatch.setattr(menu.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(menu, "get_bot_library_snapshot", fake_get_bot_library_snapshot)

    callback = SimpleNamespace(
        data="ACT:7:RND",
        message=SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )
    state = SimpleNamespace(
        set_state=AsyncMock(),
        update_data=AsyncMock(),
    )

    asyncio.run(menu.handle_library_action(callback, state))

    sent_text = callback.message.answer.await_args.args[0]
    assert "价格：【20.00】" in sent_text
