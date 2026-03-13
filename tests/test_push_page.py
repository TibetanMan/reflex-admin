from test_reflex.components.sidebar import sidebar
from test_reflex.pages.push import (
    push_campaign_table,
    push_compose_panel,
    push_left_column,
    push_page,
    push_review_table,
)


def test_push_page_has_super_admin_gate():
    rendered = repr(push_page())

    assert "is_super_admin" in rendered
    assert "shield-alert" in rendered
    assert "poll_push_dashboard" in rendered
    assert "push-auto-poll-trigger" in rendered


def test_push_review_and_compose_sections_bind_to_state_handlers():
    review_rendered = repr(push_review_table())
    compose_rendered = repr(push_compose_panel())

    assert "review_tasks" in review_rendered
    assert "approve_review_and_fill_form" in review_rendered
    assert "inventory_search_candidates" in compose_rendered
    assert "set_inventory_search_query" in compose_rendered
    assert "add_inventory_selection" in compose_rendered
    assert "remove_inventory_selection" in compose_rendered
    assert "bot_options" in compose_rendered
    assert "set_schedule_enabled" in compose_rendered
    assert "set_scheduled_publish_at" in compose_rendered
    assert "set_is_markdown_ad" in compose_rendered
    assert "queue_push_campaign" in compose_rendered
    assert "全局推送" not in compose_rendered
    assert "仅超级管理员可操作" not in review_rendered
    assert "队列 + 冗余 + 权限控制" not in compose_rendered


def test_push_campaign_table_uses_ten_rows_pagination():
    rendered = repr(push_campaign_table())

    assert "paginated_push_campaigns" in rendered
    assert "next_campaign_page" in rendered
    assert "prev_campaign_page" in rendered


def test_push_left_column_contains_review_and_campaign_sections():
    rendered = repr(push_left_column())

    assert "review_tasks" in rendered
    assert "paginated_push_campaigns" in rendered


def test_sidebar_core_features_contains_push_route():
    rendered = repr(sidebar())

    assert "/push" in rendered
