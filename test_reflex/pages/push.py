"""消息推送中心页面."""

import reflex as rx

from ..state.auth import AuthState
from ..state.push_state import PushState
from ..styles import card_style
from ..templates import template

AUTO_POLL_SCRIPT = """
if (window.__pushAutoPollTimer) {
  clearInterval(window.__pushAutoPollTimer);
}
window.__pushAutoPollTimer = window.setInterval(function () {
  var trigger = document.getElementById("push-auto-poll-trigger");
  if (!trigger) {
    clearInterval(window.__pushAutoPollTimer);
    window.__pushAutoPollTimer = null;
    return;
  }
  trigger.click();
}, 5000);
"""


def push_stat_cards() -> rx.Component:
    return rx.grid(
        rx.box(
            rx.text("待审核", size="2", color=rx.color("gray", 11)),
            rx.heading(PushState.pending_reviews_count.to(str), size="6"),
            **card_style,
        ),
        rx.box(
            rx.text("排队中", size="2", color=rx.color("gray", 11)),
            rx.heading(PushState.queued_campaigns_count.to(str), size="6"),
            **card_style,
        ),
        rx.box(
            rx.text("已发送", size="2", color=rx.color("gray", 11)),
            rx.heading(PushState.sent_campaigns_count.to(str), size="6"),
            **card_style,
        ),
        rx.box(
            rx.text("失败", size="2", color=rx.color("gray", 11)),
            rx.heading(PushState.failed_campaigns_count.to(str), size="6"),
            **card_style,
        ),
        columns="4",
        spacing="4",
        width="100%",
    )


def render_review_row(task: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.code(task["id"].to(str), size="1")),
        rx.table.cell(
            rx.vstack(
                rx.text(task["inventory_name"], size="2", weight="medium"),
                rx.text(task["merchant_name"], size="1", color=rx.color("gray", 10)),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(rx.badge(task["status"], variant="soft", color_scheme="orange")),
        rx.table.cell(rx.text(task["created_at"], size="2", color=rx.color("gray", 11))),
        rx.table.cell(
            rx.button(
                "审核通过",
                size="1",
                variant="soft",
                on_click=lambda: PushState.approve_review_and_fill_form(task["id"], AuthState.user_role),
            )
        ),
    )


def push_review_table() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("待审核库存", size="4"),
            rx.spacer(),
            rx.text("库存上传且开启推送开关后会进入此处", size="2", color=rx.color("gray", 11)),
            width="100%",
            margin_bottom="10px",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("审核号"),
                    rx.table.column_header_cell("库存"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("时间"),
                    rx.table.column_header_cell("操作"),
                )
            ),
            rx.table.body(
                rx.cond(
                    PushState.review_tasks_display.length() > 0,
                    rx.foreach(PushState.review_tasks_display, render_review_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无待审核记录", size="2", color=rx.color("gray", 10)),
                            col_span=5,
                            text_align="center",
                        )
                    ),
                )
            ),
            width="100%",
        ),
        **card_style,
        width="100%",
    )


def render_inventory_search_row(item: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(item["name"], size="2", weight="medium"),
            rx.text(f"ID: {item['id']} · 商家: {item['merchant']}", size="1", color=rx.color("gray", 10)),
            align="start",
            spacing="0",
        ),
        rx.spacer(),
        rx.button(
            "添加",
            size="1",
            variant="soft",
            on_click=lambda: PushState.add_inventory_selection(item["id"]),
        ),
        width="100%",
    )


def render_selected_inventory(item: dict) -> rx.Component:
    return rx.hstack(
        rx.text(f"{item['name']}（ID:{item['id']}）", size="2"),
        rx.spacer(),
        rx.icon_button(
            rx.icon("x", size=14),
            size="1",
            variant="ghost",
            color_scheme="gray",
            on_click=lambda: PushState.remove_inventory_selection(item["id"]),
        ),
        width="100%",
    )


def render_bot_checkbox(bot: dict) -> rx.Component:
    return rx.checkbox(
        f"{bot['name']}（{bot['owner']}）",
        checked=PushState.selected_bot_ids.contains(bot["id"]),
        on_change=lambda _: PushState.toggle_bot_selection(bot["id"]),
    )


def push_compose_panel() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("推送编排", size="4"),
                rx.spacer(),
                rx.button(
                    rx.icon("send", size=16),
                    "创建推送",
                    on_click=lambda: PushState.queue_push_campaign(AuthState.user_role),
                ),
                width="100%",
            ),
            rx.hstack(
                rx.text("定时发布", size="2"),
                rx.spacer(),
                rx.switch(
                    checked=PushState.schedule_enabled,
                    on_change=PushState.set_schedule_enabled,
                ),
                width="100%",
            ),
            rx.input(
                type="datetime-local",
                value=PushState.scheduled_publish_at,
                on_change=PushState.set_scheduled_publish_at,
                width="100%",
                disabled=~PushState.schedule_enabled,
            ),
            rx.vstack(
                rx.text("库存选择", size="2", weight="medium"),
                rx.input(
                    placeholder="按库存名称或库存ID搜索后添加",
                    value=PushState.inventory_search_query,
                    on_change=PushState.set_inventory_search_query,
                    width="100%",
                ),
                rx.box(
                    rx.cond(
                        PushState.inventory_search_candidates.length() > 0,
                        rx.vstack(
                            rx.foreach(PushState.inventory_search_candidates, render_inventory_search_row),
                            spacing="2",
                            align="start",
                            width="100%",
                        ),
                        rx.text("无匹配库存，可尝试更换关键词。", size="1", color=rx.color("gray", 10)),
                    ),
                    border=f"1px solid {rx.color('gray', 5)}",
                    border_radius="10px",
                    padding="10px",
                    width="100%",
                    max_height="160px",
                    overflow_y="auto",
                ),
                rx.hstack(
                    rx.text("已选库存", size="1", color=rx.color("gray", 11)),
                    rx.spacer(),
                    rx.button(
                        "清空",
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                        on_click=PushState.clear_inventory_selection,
                    ),
                    width="100%",
                ),
                rx.box(
                    rx.cond(
                        PushState.selected_inventory_items.length() > 0,
                        rx.vstack(
                            rx.foreach(PushState.selected_inventory_items, render_selected_inventory),
                            spacing="1",
                            align="start",
                            width="100%",
                        ),
                        rx.text("尚未选择库存。", size="1", color=rx.color("gray", 10)),
                    ),
                    border=f"1px solid {rx.color('gray', 5)}",
                    border_radius="10px",
                    padding="10px",
                    width="100%",
                    max_height="140px",
                    overflow_y="auto",
                ),
                width="100%",
                align="start",
                spacing="2",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("推送机器人（多选）", size="2", weight="medium"),
                    rx.spacer(),
                    rx.button(
                        "清空",
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                        on_click=PushState.clear_bot_selection,
                    ),
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.foreach(PushState.bot_options, render_bot_checkbox),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    border=f"1px solid {rx.color('gray', 5)}",
                    border_radius="10px",
                    padding="10px",
                    width="100%",
                    max_height="140px",
                    overflow_y="auto",
                ),
                width="100%",
                spacing="2",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("广告文案", size="2", weight="medium"),
                    rx.spacer(),
                    rx.hstack(
                        rx.text("Markdown 广告", size="1", color=rx.color("gray", 11)),
                        rx.switch(
                            checked=PushState.is_markdown_ad,
                            on_change=PushState.set_is_markdown_ad,
                        ),
                        spacing="2",
                    ),
                    width="100%",
                ),
                rx.text_area(
                    value=PushState.ad_content,
                    on_change=PushState.set_ad_content,
                    placeholder=rx.cond(
                        PushState.is_markdown_ad,
                        "填写 Markdown 广告内容",
                        "填写纯文字广告内容",
                    ),
                    rows="4",
                    width="100%",
                ),
                width="100%",
                align="start",
                spacing="1",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        **card_style,
        width="100%",
    )


def _campaign_status_badge(task: dict) -> rx.Component:
    return rx.match(
        task["status"],
        ("sent", rx.badge("已发送", variant="soft", color_scheme="green")),
        ("queued", rx.badge("排队中", variant="soft", color_scheme="orange")),
        ("failed", rx.badge("失败", variant="soft", color_scheme="red")),
        rx.badge(task["status"], variant="soft", color_scheme="gray"),
    )


def render_campaign_row(task: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.code(task["id"].to(str), size="1")),
        rx.table.cell(rx.cond(task["scope"] == "global", "全局", "库存定向")),
        rx.table.cell(_campaign_status_badge(task)),
        rx.table.cell(rx.text(task["created_at"], size="2", color=rx.color("gray", 11))),
    )


def push_campaign_table() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("推送记录", size="4"),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "刷新",
                size="1",
                variant="soft",
                on_click=PushState.refresh_push_dashboard,
            ),
            width="100%",
            margin_bottom="10px",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("任务号"),
                    rx.table.column_header_cell("库存"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("创建时间"),
                )
            ),
            rx.table.body(
                rx.cond(
                    PushState.paginated_push_campaigns.length() > 0,
                    rx.foreach(PushState.paginated_push_campaigns, render_campaign_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无推送任务", size="2", color=rx.color("gray", 10)),
                            col_span=4,
                            text_align="center",
                        )
                    ),
                )
            ),
            width="100%",
        ),
        rx.hstack(
            rx.text(
                "每页 10 条 · 显示 ",
                PushState.campaign_display_range,
                " / ",
                PushState.push_campaigns_display.length().to(str),
                size="1",
                color=rx.color("gray", 10),
            ),
            rx.spacer(),
            rx.icon_button(
                rx.icon("chevron-left", size=14),
                size="1",
                variant="soft",
                on_click=PushState.prev_campaign_page,
                disabled=PushState.campaign_page <= 1,
            ),
            rx.text(
                PushState.campaign_page.to(str),
                " / ",
                PushState.total_campaign_pages.to(str),
                size="1",
                width="72px",
                text_align="center",
            ),
            rx.icon_button(
                rx.icon("chevron-right", size=14),
                size="1",
                variant="soft",
                on_click=PushState.next_campaign_page,
                disabled=PushState.campaign_page >= PushState.total_campaign_pages,
            ),
            width="100%",
            margin_top="12px",
        ),
        **card_style,
        width="100%",
    )


def push_left_column() -> rx.Component:
    return rx.vstack(
        push_review_table(),
        rx.box(height="16px"),
        push_campaign_table(),
        width="100%",
        spacing="0",
        align="start",
    )


def super_admin_only_notice() -> rx.Component:
    return rx.box(
        rx.callout(
            "当前账号暂无该页面访问权限，请联系管理员开通。",
            icon="shield-alert",
            color_scheme="orange",
            width="100%",
        ),
        **card_style,
        width="100%",
    )


@template
def push_page() -> rx.Component:
    return rx.cond(
        AuthState.is_super_admin,
        rx.box(
            rx.button(
                "",
                id="push-auto-poll-trigger",
                on_click=PushState.poll_push_dashboard,
                style={"display": "none"},
            ),
            rx.hstack(
                rx.vstack(
                    rx.heading("消息推送", size="6"),
                    rx.text("选择库存和推送机器人，配置发布方式后创建推送。", color=rx.color("gray", 11)),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    "刷新数据",
                    variant="soft",
                    on_click=PushState.refresh_push_dashboard,
                ),
                width="100%",
                margin_bottom="24px",
            ),
            push_stat_cards(),
            rx.box(height="16px"),
            rx.grid(
                push_left_column(),
                push_compose_panel(),
                columns="2",
                spacing="4",
                width="100%",
                align="start",
            ),
            width="100%",
            on_mount=rx.call_script(AUTO_POLL_SCRIPT),
        ),
        super_admin_only_notice(),
    )
