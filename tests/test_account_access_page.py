from __future__ import annotations

import inspect
import importlib


def test_request_access_page_has_submit_form():
    module = importlib.import_module("test_reflex.pages.account_access_help")
    source = inspect.getsource(module.request_access_page)

    assert "AccountAccessRequestState.submit_request" in source
    assert "申请开通管理员账户" in source


def test_request_access_submit_copies_payload_for_admin_contact():
    module = importlib.import_module("test_reflex.pages.account_access_help")
    source = inspect.getsource(module.AccountAccessRequestState.submit_request.fn)

    assert "rx.set_clipboard(" in source
    assert "申请信息已复制" in source
