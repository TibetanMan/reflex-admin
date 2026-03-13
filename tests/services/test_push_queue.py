from services.push_queue import (
    enqueue_push_campaign,
    list_audit_logs,
    list_push_campaigns,
    list_review_tasks,
    process_push_queue,
    register_inventory_review_task,
    reset_push_storage,
)


def test_register_inventory_review_task_deduplicates_pending_records():
    reset_push_storage()

    first = register_inventory_review_task(
        inventory_id=101,
        inventory_name="US-VISA-Premium",
        merchant_name="平台自营",
    )
    second = register_inventory_review_task(
        inventory_id=101,
        inventory_name="US-VISA-Premium",
        merchant_name="平台自营",
    )

    reviews = list_review_tasks()
    assert first["id"] == second["id"]
    assert len(reviews) == 1
    assert reviews[0]["status"] == "pending_review"


def test_enqueue_push_campaign_deduplicates_by_payload_fingerprint():
    reset_push_storage()

    payload = {
        "scope": "inventory",
        "inventory_ids": [101],
        "inventory_names": ["US-VISA-Premium"],
        "bot_ids": [1, 2],
        "bot_names": ["主站 Bot", "代理A Bot"],
        "is_global": False,
        "markdown_content": "**今日上新**",
        "ad_content": "限时补货，欢迎采购",
        "priority": "high",
        "queue_partition": "primary",
        "max_retries": 3,
        "failover_enabled": True,
        "failover_channel": "telegram_backup",
        "created_by": "admin",
        "approved_by": "admin",
    }

    first = enqueue_push_campaign(payload)
    second = enqueue_push_campaign(payload)
    campaigns = list_push_campaigns()

    assert first["id"] == second["id"]
    assert len(campaigns) == 1
    assert campaigns[0]["status"] == "queued"


def test_process_push_queue_marks_records_as_sent_and_writes_audit():
    reset_push_storage()
    enqueue_push_campaign(
        {
            "scope": "global",
            "inventory_ids": [],
            "inventory_names": [],
            "bot_ids": [1],
            "bot_names": ["主站 Bot"],
            "is_global": True,
            "markdown_content": "# 全局通知",
            "ad_content": "系统维护完成",
            "priority": "normal",
            "queue_partition": "primary",
            "max_retries": 2,
            "failover_enabled": False,
            "failover_channel": "",
            "created_by": "admin",
            "approved_by": "admin",
        }
    )

    result = process_push_queue(batch_size=10)
    campaigns = list_push_campaigns()
    audit_logs = list_audit_logs()

    assert result["processed"] == 1
    assert campaigns[0]["status"] == "sent"
    assert len(audit_logs) >= 2
    assert any(log["action"] == "queued" for log in audit_logs)
    assert any(log["action"] == "sent" for log in audit_logs)


def test_process_push_queue_skips_campaign_when_schedule_not_due():
    reset_push_storage()
    enqueue_push_campaign(
        {
            "scope": "inventory",
            "inventory_ids": [102],
            "inventory_names": ["US-MC-Standard"],
            "bot_ids": [1],
            "bot_names": ["主站 Bot"],
            "is_global": False,
            "markdown_content": "# 定时通知",
            "ad_content": "晚点发送",
            "scheduled_publish_at": "2999-01-01T00:00",
            "priority": "normal",
            "queue_partition": "primary",
            "max_retries": 2,
            "failover_enabled": False,
            "failover_channel": "",
            "created_by": "admin",
            "approved_by": "admin",
        }
    )

    result = process_push_queue(batch_size=10)
    campaigns = list_push_campaigns()

    assert result["processed"] == 0
    assert campaigns[0]["status"] == "queued"
