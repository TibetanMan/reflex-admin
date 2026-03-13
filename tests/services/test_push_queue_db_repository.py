from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

import shared.models  # noqa: F401
from services.push_queue import SqlModelPushQueueRepository


def _build_sqlite_repo(tmp_path: Path) -> SqlModelPushQueueRepository:
    db_file = tmp_path / "push_queue.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)

    def _session_factory() -> Session:
        return Session(engine)

    return SqlModelPushQueueRepository(session_factory=_session_factory)


def test_sqlmodel_repository_review_dedup_and_approve_flow(tmp_path: Path):
    repo = _build_sqlite_repo(tmp_path)
    repo.reset()

    first = repo.register_review_task(
        inventory_id=101,
        inventory_name="US-VISA-Premium",
        merchant_name="Platform",
        source="inventory_import",
    )
    second = repo.register_review_task(
        inventory_id=101,
        inventory_name="US-VISA-Premium",
        merchant_name="Platform",
        source="inventory_import",
    )
    approved = repo.approve_review_task(first["id"], "super_admin")

    assert first["id"] == second["id"]
    assert approved is not None
    assert approved["status"] == "approved"
    assert any(item["id"] == first["id"] for item in repo.list_review_tasks())


def test_sqlmodel_repository_campaign_queue_and_audit_flow(tmp_path: Path):
    repo = _build_sqlite_repo(tmp_path)
    repo.reset()

    payload = {
        "scope": "inventory",
        "inventory_ids": [101],
        "inventory_names": ["US-VISA-Premium"],
        "bot_ids": [1],
        "bot_names": ["Main Bot"],
        "is_global": False,
        "markdown_content": "normal push",
        "ad_content": "ad text",
        "priority": "normal",
        "queue_partition": "primary",
        "max_retries": 2,
        "failover_enabled": False,
        "failover_channel": "",
        "created_by": "admin",
        "approved_by": "admin",
    }
    enqueued = repo.enqueue_campaign(payload)
    result = repo.process_queue(batch_size=10)
    campaigns = repo.list_campaigns()
    audits = repo.list_audit_logs()

    assert enqueued["status"] == "queued"
    assert result["processed"] == 1
    assert any(item["id"] == enqueued["id"] and item["status"] == "sent" for item in campaigns)
    assert any(item["action"] == "queued" for item in audits)
    assert any(item["action"] == "sent" for item in audits)


def test_sqlmodel_repository_campaign_cancel_flow(tmp_path: Path):
    repo = _build_sqlite_repo(tmp_path)
    repo.reset()

    payload = {
        "scope": "inventory",
        "inventory_ids": [101],
        "inventory_names": ["US-VISA-Premium"],
        "bot_ids": [1],
        "bot_names": ["Main Bot"],
        "is_global": False,
        "markdown_content": "cancel me",
        "ad_content": "ad text",
        "priority": "normal",
        "queue_partition": "primary",
        "max_retries": 2,
        "failover_enabled": False,
        "failover_channel": "",
        "created_by": "admin",
        "approved_by": "admin",
    }
    enqueued = repo.enqueue_campaign(payload)
    cancelled = repo.cancel_campaign(enqueued["id"], "admin")

    assert cancelled is not None
    assert cancelled["status"] == "cancelled"
    assert any(item["action"] == "cancelled" for item in repo.list_audit_logs())
