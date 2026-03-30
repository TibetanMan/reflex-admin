from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.handlers import menu


def test_recharge_message_mentions_campaign_bonus(monkeypatch):
    async def fake_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_runtime_ids(_message, *, tg_user=None):
        del tg_user
        return 1, 1

    async def fake_try_shortcut(_message, _state):
        return False

    def fake_create_bot_deposit(*, user_id, amount, bot_id):
        del user_id, amount, bot_id
        return {
            "id": 9,
            "to_address": "TCampaignDepositWallet001",
            "expires_at": "2026-04-10 10:00:00",
            "campaign": {
                "display_title": "首充活动",
                "display_subtitle": "首次充值即可得奖励",
                "summary": "首次充值赠送 5% + 10 USDT",
            },
        }

    monkeypatch.setattr(menu.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(menu, "_ensure_runtime_ids", fake_runtime_ids)
    monkeypatch.setattr(menu, "_try_shortcut_menu_from_state", fake_try_shortcut)
    monkeypatch.setattr(menu, "_build_recharge_qr_image", lambda **kwargs: object())
    monkeypatch.setattr(menu, "create_bot_deposit", fake_create_bot_deposit)

    message = SimpleNamespace(
        text="100",
        answer=AsyncMock(),
        answer_photo=AsyncMock(),
    )
    state = SimpleNamespace(
        clear=AsyncMock(),
    )

    asyncio.run(menu.handle_recharge_amount_input(message, state))

    sent_text = message.answer_photo.await_args.kwargs["caption"]
    assert "🎁 当前活动：首充活动" in sent_text
    assert "首次充值赠送 5% + 10 USDT" in sent_text
    assert "首次充值即可得奖励" in sent_text
