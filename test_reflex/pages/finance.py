"""Finance management page."""

import reflex as rx

from ..components.a11y import with_focus_blur
from ..state.auth import AuthState
from ..state.finance_state import FinanceState
from ..styles import card_style
from ..templates import template


def finance_stat_cards() -> rx.Component:
    """Finance statistic cards."""
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
                    rx.text("Today Deposits", size="2", color=rx.color("gray", 11)),
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
                    rx.text("Wallet Balance", size="2", color=rx.color("gray", 11)),
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
                    rx.text("Pending", size="2", color=rx.color("gray", 11)),
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
                    rx.text("Total Deposited", size="2", color=rx.color("gray", 11)),
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
    """Manual deposit dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Manual Deposit"),
            rx.dialog.description(
                "Add user balance manually.",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.text("User ID", size="2", weight="medium"),
                rx.input(
                    placeholder="Telegram ID or username",
                    value=FinanceState.manual_user_id,
                    on_change=FinanceState.set_manual_user_id,
                    width="100%",
                ),
                rx.text("Amount", size="2", weight="medium"),
                rx.input(
                    placeholder="USDT amount",
                    value=FinanceState.manual_amount,
                    on_change=FinanceState.set_manual_amount,
                    width="100%",
                    type="text",
                    input_mode="decimal",
                ),
                rx.text("Remark", size="2", weight="medium"),
                rx.text_area(
                    placeholder="Manual deposit remark",
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
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=FinanceState.close_manual_deposit_modal,
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "Confirm",
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
    """Deposit status badge."""
    return rx.match(
        record["status"],
        ("completed", rx.badge("Completed", color_scheme="green")),
        ("confirming", rx.badge("Confirming", color_scheme="orange")),
        ("pending", rx.badge("Pending", color_scheme="blue")),
        ("expired", rx.badge("Expired", color_scheme="gray")),
        ("failed", rx.badge("Failed", color_scheme="red")),
        rx.badge("Unknown", color_scheme="gray"),
    )


def render_deposit_record_row(record: dict) -> rx.Component:
    """Render one deposit row."""
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
                    content="Copy deposit number",
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
                        content="Open transaction",
                    ),
                ),
                spacing="1",
            )
        ),
    )


def deposit_list_table() -> rx.Component:
    """Deposit table bound to FinanceState."""
    return rx.box(
        rx.hstack(
            rx.text(
                f"Total {FinanceState.filtered_deposits.length()} rows",
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
                    rx.table.column_header_cell("Deposit No"),
                    rx.table.column_header_cell("User"),
                    rx.table.column_header_cell("Bot"),
                    rx.table.column_header_cell("Amount"),
                    rx.table.column_header_cell("Method"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Time"),
                    rx.table.column_header_cell("Action"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    FinanceState.filtered_deposits.length() > 0,
                    rx.foreach(FinanceState.filtered_deposits, render_deposit_record_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("No deposit records", size="2", color=rx.color("gray", 10)),
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
    """Render one wallet card."""
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
                        content="Copy address",
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
    """Wallet cards bound to FinanceState."""
    return rx.box(
        rx.text("Wallet Addresses", size="4", weight="bold", margin_bottom="16px"),
        rx.vstack(
            rx.foreach(FinanceState.wallets, render_wallet_card),
            spacing="3",
            width="100%",
        ),
    )


@template
def finance_page() -> rx.Component:
    """Finance page."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading("Finance Center", size="6"),
                rx.text("Deposit records and wallet management", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("download", size=16),
                    "Export Report",
                    variant="outline",
                    on_click=FinanceState.export_finance_report_csv,
                ),
                rx.button(
                    rx.icon("link-2", size=16),
                    "Sync On-chain",
                    variant="soft",
                    on_click=FinanceState.sync_onchain_deposits,
                ),
                rx.button(
                    rx.icon("plus", size=16),
                    "Manual Deposit",
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
                rx.text("Deposit Records", size="4", weight="bold", margin_bottom="16px"),
                rx.box(
                    rx.hstack(
                        rx.input(
                            placeholder="Search user / deposit / bot ...",
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
