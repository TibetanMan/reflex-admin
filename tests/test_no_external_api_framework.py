from __future__ import annotations

from pathlib import Path


def test_project_does_not_ship_external_api_web_app():
    assert not Path("api/app.py").exists()


def test_project_does_not_keep_external_api_package_shell():
    assert not Path("api/__init__.py").exists()
