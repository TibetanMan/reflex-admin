from __future__ import annotations

import inspect

import test_reflex.pages.bots as bots_page_module
from test_reflex.state.bot_state import BotState


def test_bots_page_uses_dynamic_owner_filter_options():
    source = inspect.getsource(bots_page_module.bots_page)
    assert "owner_filter_options" in source
    assert "\"代理商A\"" not in source
    assert "\"代理商B\"" not in source
    assert "\"代理商C\"" not in source


def test_bot_state_builds_owner_filter_options_from_owner_options():
    state = BotState()
    state.owner_options = ["平台自营", "代理商A", "代理商B"]
    options = state.owner_filter_options

    assert options[0] == "全部归属"
    assert "平台自营" in options
    assert "代理商A" in options
    assert "代理商B" in options


def test_bots_page_uses_dynamic_status_filter_options():
    source = inspect.getsource(bots_page_module.bots_page)
    assert "status_filter_options" in source
    assert "[\"全部状态\"" not in source
