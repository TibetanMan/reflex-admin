from __future__ import annotations

import csv
from pathlib import Path

import test_reflex.state.user_state as user_state_module
from test_reflex.state.user_state import UserState


def _stub_export_bridge(monkeypatch):
    updates: list[dict] = []

    monkeypatch.setattr(
        user_state_module,
        "ensure_export_task_repository_from_env",
        lambda: "memory",
    )
    monkeypatch.setattr(
        user_state_module,
        "create_export_task",
        lambda **kwargs: {"id": 42, **kwargs},
    )

    def _fake_update_export_task(**kwargs):
        updates.append(dict(kwargs))
        return dict(kwargs)

    monkeypatch.setattr(user_state_module, "update_export_task", _fake_update_export_task)
    return updates


def _read_export_rows(file_path: str) -> list[dict[str, str]]:
    path = Path(file_path)
    assert path.exists()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_export_users_all_bots_expands_rows_by_bot_account(monkeypatch, tmp_path: Path):
    updates = _stub_export_bridge(monkeypatch)
    monkeypatch.chdir(tmp_path)

    state = UserState()
    state.export_bot = "全部 Bot"
    state.export_date_from = "2026-03-01"
    state.export_date_to = "2026-03-31"
    state.users = [
        {
            "id": 1,
            "telegram_id": "10001",
            "name": "Alice",
            "username": "@alice",
            "status": "active",
            "balance": 60.0,
            "total_deposit": 100.0,
            "total_spent": 40.0,
            "orders": 4,
            "bot_sources": [
                {
                    "bot_id": 1,
                    "bot_name": "Main Bot",
                    "status": "active",
                    "balance": 10.0,
                    "total_deposit": 30.0,
                    "total_spent": 20.0,
                    "orders": 2,
                },
                {
                    "bot_id": 2,
                    "bot_name": "Alt Bot",
                    "status": "banned",
                    "balance": 50.0,
                    "total_deposit": 70.0,
                    "total_spent": 20.0,
                    "orders": 2,
                },
            ],
            "primary_bot": "Main Bot",
            "primary_bot_status": "active",
            "created_at": "2026-03-05 10:00",
            "last_active": "2026-03-08 12:00",
            "deposit_records": [],
            "purchase_records": [],
        },
        {
            "id": 2,
            "telegram_id": "10002",
            "name": "Bob",
            "username": "@bob",
            "status": "active",
            "balance": 20.0,
            "total_deposit": 30.0,
            "total_spent": 10.0,
            "orders": 1,
            "bot_sources": [
                {
                    "bot_id": 1,
                    "bot_name": "Main Bot",
                    "status": "active",
                    "balance": 20.0,
                    "total_deposit": 30.0,
                    "total_spent": 10.0,
                    "orders": 1,
                }
            ],
            "primary_bot": "Main Bot",
            "primary_bot_status": "active",
            "created_at": "2026-03-09 10:00",
            "last_active": "2026-03-09 13:00",
            "deposit_records": [],
            "purchase_records": [],
        },
    ]

    state.export_users()

    rows = _read_export_rows(state.export_file_url)

    assert state.export_status == "completed"
    assert state.export_total_records == 3
    assert len(rows) == 3
    assert {"bot_name", "bot_status", "bot_balance", "bot_total_deposit", "bot_total_spent", "bot_orders"} <= set(
        rows[0].keys()
    )

    alice_rows = [row for row in rows if row["telegram_id"] == "10001"]
    assert len(alice_rows) == 2
    assert sorted(row["bot_name"] for row in alice_rows) == ["Alt Bot", "Main Bot"]

    latest = updates[-1]
    assert latest["status"] == "completed"
    assert latest["total_records"] == 3
    assert latest["processed_records"] == 3


def test_export_users_specific_bot_exports_only_that_bot(monkeypatch, tmp_path: Path):
    _stub_export_bridge(monkeypatch)
    monkeypatch.chdir(tmp_path)

    state = UserState()
    state.export_bot = "Main Bot"
    state.export_date_from = "2026-03-01"
    state.export_date_to = "2026-03-31"
    state.users = [
        {
            "id": 1,
            "telegram_id": "10001",
            "name": "Alice",
            "username": "@alice",
            "status": "active",
            "balance": 60.0,
            "total_deposit": 100.0,
            "total_spent": 40.0,
            "orders": 4,
            "bot_sources": [
                {
                    "bot_id": 1,
                    "bot_name": "Main Bot",
                    "status": "active",
                    "balance": 10.0,
                    "total_deposit": 30.0,
                    "total_spent": 20.0,
                    "orders": 2,
                },
                {
                    "bot_id": 2,
                    "bot_name": "Alt Bot",
                    "status": "active",
                    "balance": 50.0,
                    "total_deposit": 70.0,
                    "total_spent": 20.0,
                    "orders": 2,
                },
            ],
            "primary_bot": "Main Bot",
            "primary_bot_status": "active",
            "created_at": "2026-03-05 10:00",
            "last_active": "2026-03-08 12:00",
            "deposit_records": [],
            "purchase_records": [],
        },
        {
            "id": 2,
            "telegram_id": "10002",
            "name": "Carol",
            "username": "@carol",
            "status": "active",
            "balance": 20.0,
            "total_deposit": 30.0,
            "total_spent": 10.0,
            "orders": 1,
            "bot_sources": [
                {
                    "bot_id": 2,
                    "bot_name": "Alt Bot",
                    "status": "active",
                    "balance": 20.0,
                    "total_deposit": 30.0,
                    "total_spent": 10.0,
                    "orders": 1,
                }
            ],
            "primary_bot": "Alt Bot",
            "primary_bot_status": "active",
            "created_at": "2026-03-09 10:00",
            "last_active": "2026-03-09 13:00",
            "deposit_records": [],
            "purchase_records": [],
        },
    ]

    state.export_users()
    rows = _read_export_rows(state.export_file_url)

    assert state.export_total_records == 1
    assert len(rows) == 1
    assert rows[0]["telegram_id"] == "10001"
    assert rows[0]["bot_name"] == "Main Bot"
