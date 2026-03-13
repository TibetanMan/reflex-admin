from __future__ import annotations

import test_reflex.state.user_state as user_state_module
from test_reflex.pages.settings import SettingsState
from test_reflex.state.bot_state import BotState
from test_reflex.state.finance_state import FinanceState
from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState


def test_db_only_states_start_with_empty_runtime_rows():
    user_state = UserState()
    finance_state = FinanceState()
    order_state = OrderState()

    assert user_state.users == []
    assert finance_state.deposits == []
    assert finance_state.wallets == []
    assert order_state.available_bots == []


def test_user_state_load_users_data_does_not_fallback_to_seed_rows(monkeypatch):
    state = UserState()
    state.users = [{"id": 999, "name": "legacy-seed"}]

    monkeypatch.setattr(user_state_module, "list_users_snapshot", lambda: [])

    state.load_users_data()

    assert state.users == []


def test_settings_state_starts_without_sample_seed_values():
    state = SettingsState()
    assert state.default_usdt_address == ""
    assert state.default_usdt_address_draft == ""
    assert state.usdt_query_api_url == ""
    assert state.bins_query_api_url == ""


def test_bot_state_starts_without_sample_owner_defaults():
    state = BotState()
    assert state.owner_options == []
    assert state.form_owner == ""
