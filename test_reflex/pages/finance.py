"""财务管理页面。"""

import reflex as rx

from ..components.a11y import with_focus_blur
from ..state.auth import AuthState
from ..state.finance_state import FinanceState
from ..styles import card_style
from ..templates import template


def finance_stat_cards() -> rx.Component:
    """财务统计卡片。"""
    return rx.grid(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("trending-up", size=24, color=rx.color("green", 11)),
                    padding="12px",
                    background=rx.color("green", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("今日充值", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$",
                        FinanceState.today_deposits.to(str),
                        size="6",
                        weight="bold",
                        color=rx.color("green", 11),
                    ),
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
                    rx.icon("wallet", size=24, color=rx.color("blue", 11)),
                    padding="12px",
                    background=rx.color("blue", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("钱包余额", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$",
                        FinanceState.total_balance.to(str),
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
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("clock", size=24, color=rx.color("orange", 11)),
                    padding="12px",
                    background=rx.color("orange", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("待确认", size="2", color=rx.color("gray", 11)),
                    rx.text(FinanceState.pending_deposits.to(str), size="6", weight="bold"),
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
                    rx.icon("receipt", size=24, color=rx.color("violet", 11)),
                    padding="12px",
                    background=rx.color("violet", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("累计充值", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$",
                        FinanceState.total_deposit_amount.to(str),
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
        columns="4",
        spacing="4",
        width="100%",
    )


def manual_deposit_modal() -> rx.Component:
    """手动充值弹窗。"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("手动充值"),
            rx.dialog.description(
                "为指定用户手动增加余额。",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.text("用户标识", size="2", weight="medium"),
                rx.input(
                    placeholder="Telegram ID 或用户名",
                    value=FinanceState.manual_user_id,
                    on_change=FinanceState.set_manual_user_id,
                    width="100%",
                ),
                rx.text("充值金额", size="2", weight="medium"),
                rx.input(
                    placeholder="请输入 USDT 金额",
                    value=FinanceState.manual_amount,
                    on_change=FinanceState.set_manual_amount,
                    width="100%",
                    type="text",
                    input_mode="decimal",
                ),
                rx.text("备注", size="2", weight="medium"),
                rx.text_area(
                    placeholder="请输入充值备注",
                    value=FinanceState.manual_remark,
                    on_change=FinanceState.set_manual_remark,
                    width="100%",
                    rows="2",
                ),
                spacing="3",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=FinanceState.close_manual_deposit_modal,
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "确认充值",
                    on_click=FinanceState.process_manual_deposit(AuthState.username),
                ),
                width="100%",
                margin_top="24px",
            ),
            max_width="420px",
        ),
        open=FinanceState.show_manual_deposit_modal,
        on_open_change=FinanceState.handle_manual_deposit_modal_change,
    )


def deposit_status_badge(record: dict) -> rx.Component:
    """充值状态标记。"""
    return rx.match(
        record["status"],
        ("completed", rx.badge("已完成", color_scheme="green")),
        ("confirming", rx.badge("确认中", color_scheme="orange")),
        ("pending", rx.badge("待处理", color_scheme="blue")),
        ("expired", rx.badge("已过期", color_scheme="gray")),
        ("failed", rx.badge("失败", color_scheme="red")),
        rx.badge("未知", color_scheme="gray"),
    )


def render_deposit_record_row(record: dict) -> rx.Component:
    """渲染单条充值记录。"""
    return rx.table.row(
        rx.table.cell(rx.code(record["deposit_no"], size="1")),
        rx.table.cell(rx.text(record["user"], size="2")),
        rx.table.cell(rx.text(record["bot"], size="2")),
        rx.table.cell(
            rx.text(
                "$",
                record["amount"].to(str),
                size="2",
                weight="medium",
                color=rx.color("green", 11),
            )
        ),
        rx.table.cell(rx.badge(record["method"], variant="soft")),
        rx.table.cell(deposit_status_badge(record)),
        rx.table.cell(rx.text(record["created_at"], size="2", color=rx.color("gray", 11))),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("eye", size=14),
                        variant="ghost",
                        size="1",
                        on_click=lambda: FinanceState.copy_deposit_no(record["deposit_no"]),
                    ),
                    content="复制充值单号",
                ),
                rx.cond(
                    record["tx_hash"],
                    rx.tooltip(
                        rx.icon_button(
                            rx.icon("external-link", size=14),
                            variant="ghost",
                            size="1",
                            on_click=lambda: FinanceState.open_tx_hash_link(record["tx_hash"]),
                        ),
                        content="打开链上交易",
                    ),
                ),
                spacing="1",
            )
        ),
    )


def deposit_list_table() -> rx.Component:
    """充值记录表格。"""
    return rx.box(
        rx.hstack(
            rx.text(
                f"共 {FinanceState.filtered_deposits.length()} 条记录",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            margin_bottom="12px",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("充值单号"),
                    rx.table.column_header_cell("用户"),
                    rx.table.column_header_cell("机器人"),
                    rx.table.column_header_cell("金额"),
                    rx.table.column_header_cell("方式"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("时间"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    FinanceState.filtered_deposits.length() > 0,
                    rx.foreach(FinanceState.filtered_deposits, render_deposit_record_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无充值记录", size="2", color=rx.color("gray", 10)),
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


def render_wallet_card(wallet: dict) -> rx.Component:
    """渲染钱包卡片。"""
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("wallet", size=20, color=rx.color("blue", 11)),
                padding="10px",
                background=rx.color("blue", 3),
                border_radius="10px",
            ),
            rx.vstack(
                rx.text(wallet["label"], size="2", weight="medium"),
                rx.hstack(
                    rx.code(wallet["address"], size="1"),
                    rx.tooltip(
                        rx.icon_button(
                            rx.icon("copy", size=12),
                            variant="ghost",
                            size="1",
                            on_click=lambda: FinanceState.copy_wallet_address(wallet["address"]),
                        ),
                        content="复制地址",
                    ),
                    spacing="1",
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(
                    "$",
                    wallet["balance"].to(str),
                    size="3",
                    weight="bold",
                    color=rx.color("green", 11),
                ),
                rx.text(wallet["bot"], size="1", color=rx.color("gray", 9)),
                align="end",
                spacing="0",
            ),
            width="100%",
            align="center",
        ),
        **card_style,
        width="100%",
    )


def wallet_list() -> rx.Component:
    """钱包列表。"""
    return rx.box(
        rx.text("钱包地址", size="4", weight="bold", margin_bottom="16px"),
        rx.vstack(
            rx.foreach(FinanceState.wallets, render_wallet_card),
            spacing="3",
            width="100%",
        ),
    )


@template
def finance_page() -> rx.Component:
    """财务页面。"""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading("财务中心", size="6"),
                rx.text("管理充值记录、链上同步与钱包地址", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("download", size=16),
                    "导出报表",
                    variant="outline",
                    on_click=FinanceState.export_finance_report_csv,
                ),
                rx.button(
                    rx.icon("link-2", size=16),
                    "同步链上",
                    variant="soft",
                    on_click=FinanceState.sync_onchain_deposits,
                ),
                rx.button(
                    rx.icon("plus", size=16),
                    "手动充值",
                    on_click=with_focus_blur(FinanceState.open_manual_deposit_modal),
                ),
                spacing="2",
            ),
            width="100%",
            margin_bottom="24px",
        ),
        finance_stat_cards(),
        rx.box(height="24px"),
        rx.grid(
            rx.box(
                rx.text("充值记录", size="4", weight="bold", margin_bottom="16px"),
                rx.box(
                    rx.hstack(
                        rx.input(
                            placeholder="搜索用户 / 充值单号 / 机器人...",
                            value=FinanceState.search_query,
                            on_change=FinanceState.set_search_query,
                            width="240px",
                        ),
                        rx.select(
                            FinanceState.status_options,
                            value=FinanceState.filter_status,
                            on_change=FinanceState.set_filter_status,
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("refresh-cw", size=16),
                            variant="soft",
                            on_click=FinanceState.refresh_list,
                        ),
                        width="100%",
                        spacing="2",
                    ),
                    margin_bottom="16px",
                ),
                deposit_list_table(),
                grid_column="span 2",
            ),
            wallet_list(),
            columns="3",
            spacing="4",
            width="100%",
        ),
        manual_deposit_modal(),
        width="100%",
        on_mount=FinanceState.load_finance_data,
    )
