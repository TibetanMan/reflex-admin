from __future__ import annotations

import inspect

import test_reflex.pages.finance as finance_page_module
import test_reflex.state.finance_state as finance_state_module
from test_reflex.state.finance_state import FinanceState


def test_finance_page_uses_chinese_text_labels():
    source = inspect.getsource(finance_page_module)

    assert "Finance Center" not in source
    assert "Manual Deposit" not in source
    assert "Deposit Records" not in source
    assert "Wallet Addresses" not in source
    assert "Export Report" not in source
    assert "财务中心" in source
    assert "手动充值" in source
    assert "充值记录" in source
    assert "钱包地址" in source
    assert "导出报表" in source


def test_finance_state_uses_chinese_status_and_feedback():
    module_source = inspect.getsource(finance_state_module)
    class_source = inspect.getsource(FinanceState)

    assert '"All Status"' not in module_source
    assert '"Completed"' not in module_source
    assert '"Confirming"' not in module_source
    assert '"全部状态"' in module_source
    assert '"已完成"' in module_source
    assert '"确认中"' in module_source
    assert "财务数据已刷新" in class_source
