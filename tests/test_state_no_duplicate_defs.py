from __future__ import annotations

import inspect
import re

from test_reflex.state.finance_state import FinanceState
from test_reflex.state.order_state import OrderState
from test_reflex.state.user_state import UserState


def _count_method_defs(class_source: str, method_name: str) -> int:
    pattern = re.compile(
        rf"^\s+(?:async\s+)?def\s+{re.escape(method_name)}\s*\(",
        re.MULTILINE,
    )
    return len(pattern.findall(class_source))


def test_order_state_has_no_duplicate_core_methods():
    source = inspect.getsource(OrderState)
    method_names = [
        "process_refund",
        "open_export_modal",
        "export_orders",
        "run_export_task",
        "download_export_file",
        "refresh_order",
        "refresh_list",
    ]

    for name in method_names:
        assert _count_method_defs(source, name) == 1


def test_user_state_has_no_duplicate_export_methods():
    source = inspect.getsource(UserState)
    method_names = [
        "open_export_modal",
        "export_users",
        "download_export_file",
    ]

    for name in method_names:
        assert _count_method_defs(source, name) == 1


def test_finance_state_has_no_duplicate_core_methods():
    source = inspect.getsource(FinanceState)
    method_names = [
        "refresh_list",
        "process_manual_deposit",
        "load_finance_data",
    ]

    for name in method_names:
        assert _count_method_defs(source, name) == 1
