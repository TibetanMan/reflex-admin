from __future__ import annotations

import importlib
import inspect

import test_reflex.test_reflex as app_entry_module


def test_login_page_has_real_register_and_forgot_password_routes():
    login_page_module = importlib.import_module("test_reflex.pages.login")
    source = inspect.getsource(login_page_module.login)

    assert "href=\"#\"" not in source
    assert "/account/request-access" in source
    assert "/account/password-reset-help" in source


def test_app_registers_account_access_help_pages():
    source = inspect.getsource(app_entry_module)

    assert 'route="/account/request-access"' in source
    assert 'route="/account/password-reset-help"' in source


def test_login_page_removes_test_accounts_and_third_party_logins():
    login_page_module = importlib.import_module("test_reflex.pages.login")
    source = inspect.getsource(login_page_module.login)

    assert "测试账号" not in source
    assert "OAuth login is not enabled" not in source
    assert 'icon("github"' not in source
    assert 'icon("twitter"' not in source
