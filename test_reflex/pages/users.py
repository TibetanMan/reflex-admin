"""用户管理页面"""

import reflex as rx

from ..components.a11y import with_focus_blur
from ..state.auth import AuthState
from ..state.user_state import UserState
from ..styles import card_style
from ..templates import template

USER_EXPORT_AUTO_POLL_SCRIPT = """
if (window.__userExportAutoPollTimer) {
  clearInterval(window.__userExportAutoPollTimer);
}
var trigger = document.getElementById("user-export-auto-poll-trigger");
if (trigger) {
  trigger.click();
}
window.__userExportAutoPollTimer = window.setInterval(function () {
  var pollTrigger = document.getElementById("user-export-auto-poll-trigger");
  if (!pollTrigger) {
    clearInterval(window.__userExportAutoPollTimer);
    window.__userExportAutoPollTimer = null;
    return;
  }
  pollTrigger.click();
}, 5000);
"""


def user_stat_cards() -> rx.Component:
    """用户统计卡片"""
    return rx.grid(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("users", size=24, color=rx.color("blue", 11)),
                    padding="12px",
                    background=rx.color("blue", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总用户", size="2", color=rx.color("gray", 11)),
                    rx.text(UserState.total_users, size="6", weight="bold"),
                    align="end",
                    spacing="1",
                ),
                width="100%",
                justify="between",
            ),
            **card_style,
        ),
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("user_check", size=24, color=rx.color("green", 11)),
                    padding="12px",
                    background=rx.color("green", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("活跃用户", size="2", color=rx.color("gray", 11)),
                    rx.text(UserState.active_users, size="6", weight="bold"),
                    align="end",
                    spacing="1",
                ),
                width="100%",
                justify="between",
            ),
            **card_style,
        ),
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("wallet", size=24, color=rx.color("orange", 11)),
                    padding="12px",
                    background=rx.color("orange", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总余额", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$",
                        UserState.total_balance.to(str),
                        size="6",
                        weight="bold",
                    ),
                    align="end",
                    spacing="1",
                ),
                width="100%",
                justify="between",
            ),
            **card_style,
        ),
        columns="3",
        spacing="4",
        width="100%",
    )


def user_status_badge(user: dict) -> rx.Component:
    return rx.cond(
        user["status"] == "active",
        rx.badge("正常", color_scheme="green"),
        rx.badge("封禁", color_scheme="red"),
    )


def user_source_bots(user: dict) -> rx.Component:
    return rx.tooltip(
        rx.badge(
            user["source_bots_label"],
            variant="soft",
            color_scheme="blue",
            size="1",
        ),
        content="来源 Bot（多来源已合并展示）",
    )


def user_actions(user: dict) -> rx.Component:
    return rx.hstack(
        rx.tooltip(
            rx.icon_button(
                rx.icon("eye", size=14),
                variant="ghost",
                size="1",
                on_click=lambda: with_focus_blur(UserState.open_detail_modal(user["id"])),
            ),
            content="查看详情",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("wallet", size=14),
                variant="ghost",
                size="1",
                color_scheme="green",
                on_click=lambda: with_focus_blur(UserState.open_balance_modal(user["id"])),
            ),
            content="余额操作",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.cond(
                    user["primary_bot_status"] == "banned",
                    rx.icon("check", size=14),
                    rx.icon("ban", size=14),
                ),
                variant="ghost",
                size="1",
                color_scheme=rx.cond(user["primary_bot_status"] == "banned", "green", "red"),
                on_click=lambda: UserState.toggle_ban(
                    user["id"],
                    AuthState.username,
                    "bot",
                    user["primary_bot"],
                ),
            ),
            content=rx.cond(user["primary_bot_status"] == "banned", "解除 Bot 封禁", "封禁当前 Bot"),
        ),
        rx.tooltip(
            rx.icon_button(
                rx.cond(
                    user["status"] == "banned",
                    rx.icon("shield_check", size=14),
                    rx.icon("shield_alert", size=14),
                ),
                variant="ghost",
                size="1",
                color_scheme=rx.cond(user["status"] == "banned", "green", "orange"),
                on_click=lambda: UserState.toggle_ban(
                    user["id"],
                    AuthState.username,
                    "global",
                    "",
                ),
            ),
            content=rx.cond(user["status"] == "banned", "解除全局封禁", "全局封禁"),
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("history", size=14),
                variant="ghost",
                size="1",
                color_scheme="purple",
                on_click=lambda: with_focus_blur(UserState.open_user_activity_drawer(user["id"])),
            ),
            content="查看充值/购买记录",
        ),
        spacing="1",
    )


def render_user_row(user: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.avatar(fallback=user["avatar_fallback"], size="2"),
                rx.vstack(
                    rx.text(user["name"], size="2", weight="medium"),
                    rx.text(
                        rx.cond(user["username"], user["username"], "-"),
                        size="1",
                        color=rx.color("gray", 9),
                    ),
                    align="start",
                    spacing="0",
                ),
                spacing="2",
                align="center",
            )
        ),
        rx.table.cell(
            rx.tooltip(
                rx.button(
                    rx.code(user["telegram_id"], size="1"),
                    variant="ghost",
                    size="1",
                    on_click=lambda: UserState.copy_telegram_id(user["telegram_id"]),
                ),
                content="点击复制 Telegram ID",
            )
        ),
        rx.table.cell(
            rx.text(
                "$",
                user["balance_text"],
                size="2",
                weight="medium",
                color=rx.color("green", 11),
            )
        ),
        rx.table.cell(rx.text("$", user["total_deposit_text"], size="2")),
        rx.table.cell(rx.text(user["orders"].to(str), size="2")),
        rx.table.cell(user_status_badge(user)),
        rx.table.cell(user_source_bots(user)),
        rx.table.cell(user_actions(user)),
    )


def user_list_table() -> rx.Component:
    """用户列表表格"""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("用户"),
                    rx.table.column_header_cell("Telegram ID"),
                    rx.table.column_header_cell("余额"),
                    rx.table.column_header_cell("累计充值"),
                    rx.table.column_header_cell("订单数"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("来源 Bot"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    UserState.filtered_total > 0,
                    rx.foreach(UserState.paginated_users, render_user_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无符合条件的用户", size="2", color=rx.color("gray", 10)),
                            col_span=8,
                            text_align="center",
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        **card_style,
        width="100%",
    )


def balance_modal() -> rx.Component:
    """余额操作弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("余额操作"),
            rx.dialog.description(
                f"正在操作用户「{UserState.selected_user_name}」的余额",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.callout(
                    rx.hstack(
                        rx.text("当前余额:", size="2", weight="medium"),
                        rx.text(
                            UserState.selected_user_current_balance_label,
                            size="2",
                            weight="bold",
                            color=rx.color("green", 11),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    icon="wallet",
                    color_scheme="blue",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("来源 Bot", size="2", weight="medium"),
                    rx.select(
                        UserState.selected_user_bot_source_options,
                        value=UserState.selected_source_bot,
                        on_change=UserState.set_selected_source_bot,
                        width="100%",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                rx.radio_group(
                    ["充值", "扣款"],
                    value=UserState.balance_action,
                    direction="row",
                    on_change=UserState.set_balance_action,
                ),
                rx.vstack(
                    rx.text("金额", size="2", weight="medium"),
                    rx.input(
                        placeholder="0.00",
                        value=UserState.balance_amount,
                        on_change=UserState.set_balance_amount,
                        on_blur=UserState.normalize_balance_amount,
                        width="100%",
                        type="text",
                        input_mode="decimal",
                    ),
                    rx.text(
                        "金额为必填，最多 2 位小数，例如 15.20",
                        size="1",
                        color=rx.color("gray", 10),
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("备注", size="2", weight="medium"),
                    rx.text_area(
                        placeholder="请输入备注（必填）",
                        value=UserState.balance_remark,
                        on_change=UserState.set_balance_remark,
                        width="100%",
                        rows="2",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=UserState.close_balance_modal,
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "确认",
                    on_click=UserState.request_balance_confirmation,
                    color_scheme="blue",
                ),
                width="100%",
                margin_top="24px",
            ),
            max_width="460px",
        ),
        open=UserState.show_balance_modal,
        on_open_change=UserState.handle_balance_modal_change,
    )


def balance_confirm_modal() -> rx.Component:
    """余额二次确认弹窗"""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("确认余额变更"),
            rx.alert_dialog.description(
                "请再次确认本次余额操作，提交后将推送到后端。",
                size="2",
            ),
            rx.vstack(
                rx.callout(
                    UserState.balance_confirm_summary,
                    icon="triangle_alert",
                    color_scheme="orange",
                    width="100%",
                ),
                spacing="3",
                width="100%",
                margin_top="12px",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "返回修改",
                        variant="soft",
                        color_scheme="gray",
                        on_click=UserState.close_balance_confirm_modal,
                    ),
                ),
                rx.spacer(),
                rx.alert_dialog.action(
                    rx.button(
                        "确认提交",
                        color_scheme="blue",
                        on_click=UserState.confirm_balance_adjustment(AuthState.username),
                    ),
                ),
                width="100%",
                margin_top="16px",
            ),
        ),
        open=UserState.show_balance_confirm_modal,
    )


def user_detail_modal() -> rx.Component:
    """用户详情弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("用户详情"),
            rx.dialog.description(
                f"当前查看用户「{UserState.selected_user_name}」",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.grid(
                    rx.text("Telegram ID", size="2", color=rx.color("gray", 11)),
                    rx.hstack(
                        rx.code(
                            UserState.selected_user_telegram_id,
                            size="1",
                            style={"display": "inline-flex", "width": "fit-content"},
                        ),
                        rx.tooltip(
                            rx.icon_button(
                                rx.icon("copy", size=12),
                                variant="ghost",
                                size="1",
                                on_click=lambda: UserState.copy_telegram_id(
                                    UserState.selected_user_telegram_id
                                ),
                            ),
                            content="复制 Telegram ID",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.text("用户名", size="2", color=rx.color("gray", 11)),
                    rx.hstack(
                        rx.code(
                            UserState.selected_user_username,
                            size="1",
                            style={"display": "inline-flex", "width": "fit-content"},
                        ),
                        rx.tooltip(
                            rx.icon_button(
                                rx.icon("copy", size=12),
                                variant="ghost",
                                size="1",
                                on_click=lambda: UserState.copy_username(
                                    UserState.selected_user_username
                                ),
                            ),
                            content="复制用户名",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.text("余额", size="2", color=rx.color("gray", 11)),
                    rx.text("$", UserState.selected_user_balance, size="2", weight="medium"),
                    rx.text("累计充值", size="2", color=rx.color("gray", 11)),
                    rx.text("$", UserState.selected_user_total_deposit, size="2"),
                    rx.text("订单数", size="2", color=rx.color("gray", 11)),
                    rx.text(UserState.selected_user_orders, size="2"),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("来源 Bot（支持多来源）", size="2", weight="medium"),
                    rx.badge(UserState.selected_user_source_bots_label, variant="soft", color_scheme="blue"),
                    rx.select(
                        UserState.selected_user_bot_source_options,
                        value=UserState.selected_source_bot,
                        on_change=UserState.set_selected_source_bot,
                        width="100%",
                    ),
                    align="start",
                    spacing="2",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                margin_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "关闭",
                        variant="soft",
                        color_scheme="gray",
                        on_click=UserState.close_detail_modal,
                    ),
                ),
                width="100%",
                margin_top="16px",
            ),
            max_width="560px",
        ),
        open=UserState.show_detail_modal,
        on_open_change=UserState.handle_detail_modal_change,
    )


def export_modal() -> rx.Component:
    """导出用户弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("download", size=20),
                    rx.text("导出用户"),
                    spacing="2",
                ),
            ),
            rx.dialog.description(
                "选择来源 Bot 和时间范围，生成用户导出文件",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.vstack(
                    rx.text("选择 Bot", size="2", weight="medium"),
                    rx.select(
                        UserState.export_bot_options,
                        value=UserState.export_bot,
                        on_change=UserState.set_export_bot,
                        disabled=UserState.is_exporting,
                        width="100%",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("开始日期", size="2", weight="medium"),
                        rx.input(
                            type="date",
                            value=UserState.export_date_from,
                            on_change=UserState.set_export_date_from,
                            disabled=UserState.is_exporting,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("结束日期", size="2", weight="medium"),
                        rx.input(
                            type="date",
                            value=UserState.export_date_to,
                            on_change=UserState.set_export_date_to,
                            disabled=UserState.is_exporting,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.callout(
                    "导出内容包含多来源 Bot 信息，结构兼容后续数据库对接",
                    icon="info",
                    color_scheme="blue",
                    width="100%",
                ),
                rx.cond(
                    UserState.is_exporting,
                    rx.vstack(
                        rx.progress(value=UserState.export_progress, width="100%"),
                        rx.hstack(
                            rx.text(UserState.export_message, size="2", color=rx.color("gray", 11)),
                            rx.spacer(),
                            rx.text(
                                UserState.export_record_progress_text,
                                size="2",
                                color=rx.color("gray", 11),
                            ),
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                rx.cond(
                    UserState.export_can_download,
                    rx.callout(
                        UserState.export_message,
                        icon="circle_check",
                        color_scheme="green",
                        width="100%",
                    ),
                ),
                rx.cond(
                    UserState.export_is_failed,
                    rx.callout(
                        UserState.export_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button("取消", variant="soft", color_scheme="gray"),
                ),
                rx.spacer(),
                rx.cond(
                    UserState.export_can_download,
                    rx.button(
                        rx.icon("download", size=16),
                        "下载文件",
                        variant="soft",
                        color_scheme="green",
                        on_click=UserState.download_export_file,
                    ),
                ),
                rx.button(
                    rx.icon("download", size=16),
                    "开始导出",
                    on_click=UserState.export_users,
                    loading=UserState.is_exporting,
                    disabled=UserState.is_exporting,
                ),
                width="100%",
                margin_top="20px",
            ),
            max_width="520px",
        ),
        open=UserState.show_export_modal,
        on_open_change=UserState.handle_export_modal_change,
    )


def render_deposit_record_row(record: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.code(record["record_no"], size="1")),
        rx.table.cell(rx.badge(record["action"], variant="soft", color_scheme="blue")),
        rx.table.cell(rx.text("$", record["amount"].to(str), size="2", weight="medium")),
        rx.table.cell(rx.text(record["bot_name"], size="2")),
        rx.table.cell(rx.text(record["remark"], size="2")),
        rx.table.cell(rx.text(record["created_at"], size="2", color=rx.color("gray", 11))),
    )


def render_purchase_record_row(record: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.code(record["order_no"], size="1")),
        rx.table.cell(rx.text(record["item"], size="2")),
        rx.table.cell(rx.text("$", record["amount"].to(str), size="2", weight="medium")),
        rx.table.cell(rx.badge(record["status"], variant="soft", color_scheme="green")),
        rx.table.cell(rx.text(record["bot_name"], size="2")),
        rx.table.cell(rx.text(record["created_at"], size="2", color=rx.color("gray", 11))),
    )


def user_activity_drawer() -> rx.Component:
    """用户充值/购买记录抽屉"""
    return rx.drawer.root(
        rx.drawer.portal(
            rx.drawer.overlay(background="rgba(0, 0, 0, 0.35)"),
            rx.drawer.content(
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.drawer.title("用户记录"),
                            rx.drawer.description(
                                f"用户：{UserState.selected_user_name}",
                                size="2",
                                color=rx.color("gray", 11),
                            ),
                            align="start",
                            spacing="0",
                        ),
                        rx.spacer(),
                        rx.drawer.close(
                            rx.icon_button(
                                rx.icon("x", size=16),
                                variant="ghost",
                                size="1",
                            ),
                        ),
                        width="100%",
                    ),
                    rx.scroll_area(
                        rx.vstack(
                            rx.box(
                                rx.text("充值记录", size="3", weight="medium", margin_bottom="8px"),
                                rx.cond(
                                    UserState.has_selected_user_deposit_records,
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell("记录号"),
                                                rx.table.column_header_cell("类型"),
                                                rx.table.column_header_cell("金额"),
                                                rx.table.column_header_cell("来源 Bot"),
                                                rx.table.column_header_cell("备注"),
                                                rx.table.column_header_cell("时间"),
                                            )
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                UserState.selected_user_deposit_records,
                                                render_deposit_record_row,
                                            )
                                        ),
                                        width="100%",
                                        size="1",
                                    ),
                                    rx.text("暂无充值记录", size="2", color=rx.color("gray", 10)),
                                ),
                                width="100%",
                            ),
                            rx.box(
                                rx.text("购买记录", size="3", weight="medium", margin_bottom="8px"),
                                rx.cond(
                                    UserState.has_selected_user_purchase_records,
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell("订单号"),
                                                rx.table.column_header_cell("商品"),
                                                rx.table.column_header_cell("金额"),
                                                rx.table.column_header_cell("状态"),
                                                rx.table.column_header_cell("来源 Bot"),
                                                rx.table.column_header_cell("时间"),
                                            )
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                UserState.selected_user_purchase_records,
                                                render_purchase_record_row,
                                            )
                                        ),
                                        width="100%",
                                        size="1",
                                    ),
                                    rx.text("暂无购买记录", size="2", color=rx.color("gray", 10)),
                                ),
                                width="100%",
                            ),
                            spacing="6",
                            width="100%",
                        ),
                        max_height="calc(100vh - 96px)",
                        scrollbars="vertical",
                        width="100%",
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="520px",
                max_width="100vw",
                height="100vh",
                padding="20px",
                background=rx.color("gray", 1),
                border_left=f"1px solid {rx.color('gray', 4)}",
                box_shadow="0 10px 40px rgba(15, 23, 42, 0.18)",
            )
        ),
        open=UserState.show_user_activity_drawer,
        on_open_change=UserState.handle_user_activity_drawer_change,
        direction="right",
    )


def render_recent_user_export_row(task: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.code(task["id"].to(str), size="1")),
        rx.table.cell(rx.badge(task["status"], variant="soft")),
        rx.table.cell(rx.text(task["progress"].to(str), "%", size="2")),
        rx.table.cell(
            rx.text(
                task["processed_records"].to(str),
                "/",
                task["total_records"].to(str),
                size="2",
            )
        ),
        rx.table.cell(
            rx.cond(
                task["can_download"],
                rx.button(
                    rx.icon("download", size=14),
                    "Download",
                    size="1",
                    variant="soft",
                    color_scheme="green",
                    on_click=lambda: UserState.download_export_task_by_id(task["id"]),
                ),
                rx.text("-", size="2", color=rx.color("gray", 10)),
            )
        ),
    )


def recent_user_export_tasks_section() -> rx.Component:
    return rx.box(
        rx.button(
            "",
            id="user-export-auto-poll-trigger",
            on_click=UserState.poll_export_task_status,
            style={"display": "none"},
        ),
        rx.hstack(
            rx.heading("Recent Export Tasks", size="4"),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                size="1",
                variant="soft",
                on_click=UserState.poll_export_task_status,
            ),
            width="100%",
            margin_bottom="10px",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Task ID"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Progress"),
                    rx.table.column_header_cell("Processed"),
                    rx.table.column_header_cell("Action"),
                )
            ),
            rx.table.body(
                rx.cond(
                    UserState.recent_export_tasks.length() > 0,
                    rx.foreach(UserState.recent_export_tasks, render_recent_user_export_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("No export tasks yet", size="2", color=rx.color("gray", 10)),
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
        margin_top="16px",
    )


@template
def users_page() -> rx.Component:
    """用户管理页面"""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading("用户管理", size="6"),
                rx.text("管理平台用户和余额", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=16),
                "导出用户",
                variant="outline",
                on_click=with_focus_blur(UserState.open_export_modal),
            ),
            width="100%",
            margin_bottom="24px",
        ),
        user_stat_cards(),
        rx.box(height="24px"),
        rx.box(
            rx.hstack(
                rx.input(
                    placeholder="搜索用户名或 Telegram ID...",
                    value=UserState.search_query,
                    on_change=UserState.set_search_query,
                    width="280px",
                ),
                rx.select(
                    ["全部状态", "正常", "封禁"],
                    value=UserState.filter_status,
                    on_change=UserState.set_filter_status,
                ),
                rx.select(
                    UserState.bot_filter_options,
                    value=UserState.filter_bot,
                    on_change=UserState.set_filter_bot,
                    width="180px",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    "刷新",
                    variant="soft",
                    on_click=UserState.refresh_list,
                ),
                width="100%",
                spacing="3",
            ),
            **card_style,
            width="100%",
            margin_bottom="16px",
        ),
        user_list_table(),
        recent_user_export_tasks_section(),
        rx.hstack(
            rx.text(
                f"显示 {UserState.display_range} / {UserState.filtered_total}",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            rx.hstack(
                rx.text("每页:", size="2", color=rx.color("gray", 11)),
                rx.select(
                    ["20", "30", "40", "50"],
                    default_value="20",
                    on_change=UserState.set_page_size,
                    size="1",
                ),
                spacing="2",
                align="center",
            ),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=14),
                    size="1",
                    variant="soft",
                    on_click=UserState.first_page,
                    disabled=UserState.current_page <= 1,
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=14),
                    size="1",
                    variant="soft",
                    on_click=UserState.prev_page,
                    disabled=UserState.current_page <= 1,
                ),
                rx.text(
                    f"{UserState.current_page} / {UserState.total_pages}",
                    size="2",
                    width="80px",
                    text_align="center",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=UserState.next_page,
                    disabled=UserState.current_page >= UserState.total_pages,
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=UserState.last_page,
                    disabled=UserState.current_page >= UserState.total_pages,
                ),
                spacing="1",
                align="center",
            ),
            margin_top="16px",
            width="100%",
        ),
        balance_modal(),
        balance_confirm_modal(),
        user_detail_modal(),
        export_modal(),
        user_activity_drawer(),
        width="100%",
        on_mount=[UserState.load_users_data, rx.call_script(USER_EXPORT_AUTO_POLL_SCRIPT)],
    )
