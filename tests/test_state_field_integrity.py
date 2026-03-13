from __future__ import annotations

from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState
import test_reflex.state.user_state as user_state_module


def test_user_state_ui_defaults_are_declared_and_aligned():
    state = UserState()

    assert hasattr(state, "search_query")
    assert hasattr(state, "filter_status")
    assert hasattr(state, "filter_bot")
    assert hasattr(state, "balance_action")
    assert hasattr(state, "export_total_records")
    assert hasattr(state, "export_processed_records")

    assert state.filter_status == "全部状态"
    assert state.balance_action == "充值"


def test_user_state_accepts_balance_action_labels_from_ui():
    state = UserState()

    state.set_balance_action("扣款")
    assert state.balance_action == "扣款"

    state.set_balance_action("充值")
    assert state.balance_action == "充值"


def test_order_state_sort_and_filter_defaults_align_with_ui_labels():
    state = OrderState()

    assert state.filter_status == "全部状态"
    assert state.status_options == ["全部状态", "已完成", "待处理", "已退款", "已取消"]

    state.set_sort_order("最新优先")
    assert state.sort_order == "desc"

    state.set_sort_order("最早优先")
    assert state.sort_order == "asc"


def test_user_state_balance_adjustment_maps_deduct_action_to_debit(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_adjust_user_balance(**kwargs):
        captured.update({k: str(v) for k, v in kwargs.items()})
        return {}

    monkeypatch.setattr(user_state_module, "adjust_user_balance", _fake_adjust_user_balance)

    state = UserState()
    state.users = [
        {
            "id": 1,
            "telegram_id": "10001",
            "username": "@demo",
            "name": "Demo",
            "balance": 100.0,
            "total_deposit": 100.0,
            "total_spent": 0.0,
            "orders": 0,
            "status": "active",
            "bot_sources": [{"bot_id": 1, "bot_name": "Main Bot"}],
            "primary_bot": "Main Bot",
            "created_at": "2026-03-01",
            "last_active": "2026-03-06 10:00",
            "deposit_records": [],
            "purchase_records": [],
        }
    ]

    state.selected_user_id = 1
    state.selected_user = state._normalize_user(state.users[0])
    state.selected_source_bot = "Main Bot"
    state.balance_action = "扣款"
    state.balance_amount = "10.00"
    state.balance_remark = "manual debit"

    state.request_balance_confirmation()
    state.confirm_balance_adjustment()

    assert captured["action"] == "debit"


def test_user_state_filter_status_matches_users_page_labels():
    state = UserState()
    state.users = [
        {
            "id": 1,
            "telegram_id": "10001",
            "username": "@active",
            "name": "Active",
            "balance": 10.0,
            "total_deposit": 10.0,
            "total_spent": 0.0,
            "orders": 1,
            "status": "active",
            "bot_sources": [{"bot_id": 1, "bot_name": "Main Bot"}],
            "primary_bot": "Main Bot",
            "created_at": "2026-03-01",
            "last_active": "2026-03-06 10:00",
            "deposit_records": [],
            "purchase_records": [],
        },
        {
            "id": 2,
            "telegram_id": "10002",
            "username": "@banned",
            "name": "Banned",
            "balance": 10.0,
            "total_deposit": 10.0,
            "total_spent": 0.0,
            "orders": 1,
            "status": "banned",
            "bot_sources": [{"bot_id": 1, "bot_name": "Main Bot"}],
            "primary_bot": "Main Bot",
            "created_at": "2026-03-01",
            "last_active": "2026-03-06 10:00",
            "deposit_records": [],
            "purchase_records": [],
        },
    ]

    state.filter_status = "正常"
    active_rows = state.filtered_users
    assert len(active_rows) == 1
    assert active_rows[0]["status"] == "active"

    state.filter_status = "封禁"
    banned_rows = state.filtered_users
    assert len(banned_rows) == 1
    assert banned_rows[0]["status"] == "banned"


def test_bot_filter_defaults_are_readable_labels():
    user_state = UserState()
    order_state = OrderState()

    assert user_state.filter_bot == "全部 Bot"
    assert user_state.export_bot == "全部 Bot"
    assert order_state.filter_bot == "全部 Bot"
