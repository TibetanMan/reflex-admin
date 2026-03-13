from test_reflex.pages.orders import orders_page
from test_reflex.pages.users import users_page


def test_orders_page_registers_export_poll_trigger_and_recent_tasks_section():
    rendered = repr(orders_page())

    assert "order-export-auto-poll-trigger" in rendered
    assert "poll_export_task_status" in rendered
    assert "recent_export_tasks" in rendered
    assert "download_export_task_by_id" in rendered


def test_users_page_registers_export_poll_trigger_and_recent_tasks_section():
    rendered = repr(users_page())

    assert "user-export-auto-poll-trigger" in rendered
    assert "poll_export_task_status" in rendered
    assert "recent_export_tasks" in rendered
    assert "download_export_task_by_id" in rendered

