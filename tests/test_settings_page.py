import importlib

from test_reflex.pages.settings import (
    SettingsState,
    bins_query_api_section,
    default_usdt_address_section,
    settings,
    telegram_push_section,
    usdt_query_api_section,
)

settings_module = importlib.import_module("test_reflex.pages.settings")


def _unicode_escape(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii").replace("\\", "\\\\")


def test_default_usdt_address_change_requires_confirmation_before_apply():
    state = SettingsState()
    original = state.default_usdt_address
    next_address = "TNEW1234567890USDTADDRESS"

    state.set_default_usdt_address_draft(next_address)
    state.request_default_usdt_address_change()

    assert state.show_default_usdt_confirm_modal is True
    assert state.pending_default_usdt_address == next_address
    assert state.default_usdt_address == original


def test_confirm_default_usdt_address_change_applies_value_and_closes_modal(monkeypatch):
    state = SettingsState()
    next_address = "TCONFIRM1234567890USDTADDRESS"

    def _fake_update_default_usdt_address(*, address: str, operator_username: str):
        assert address == next_address
        assert operator_username == "admin"
        return {"default_usdt_address": next_address}

    monkeypatch.setattr(
        settings_module,
        "update_default_usdt_address",
        _fake_update_default_usdt_address,
    )

    state.set_default_usdt_address_draft(next_address)
    state.request_default_usdt_address_change()
    state.confirm_default_usdt_address_change()

    assert state.default_usdt_address == next_address
    assert state.default_usdt_address_draft == next_address
    assert state.show_default_usdt_confirm_modal is False
    assert state.pending_default_usdt_address == ""


def test_settings_page_wires_required_sections_and_confirmation_actions():
    page_rendered = repr(settings())
    usdt_address_rendered = repr(default_usdt_address_section())
    usdt_api_rendered = repr(usdt_query_api_section())
    bins_api_rendered = repr(bins_query_api_section())
    telegram_rendered = repr(telegram_push_section())

    assert _unicode_escape("默认 USDT 收款地址") in usdt_address_rendered
    assert _unicode_escape("USDT 交易查询接口") in usdt_api_rendered
    assert _unicode_escape("BINS 查询接口") in bins_api_rendered
    assert _unicode_escape("Telegram 消息推送设置") in telegram_rendered
    assert "request_default_usdt_address_change" in page_rendered
    assert "confirm_default_usdt_address_change" in page_rendered
    assert "show_default_usdt_confirm_modal" in page_rendered
    assert "Save address" not in usdt_address_rendered
    assert "USDT Query API" not in usdt_api_rendered
    assert "BINS Query API" not in bins_api_rendered
    assert "Telegram Push Settings" not in telegram_rendered


def test_settings_page_uses_two_column_card_grid_layout():
    rendered = repr(settings())

    assert "gridTemplateColumns" in rendered
    assert "repeat(2, minmax(0, 1fr))" in rendered
