"""Agent management page."""

import reflex as rx

from ..components.a11y import with_focus_blur
from ..state.agent_state import AgentState
from ..state.auth import AuthState
from ..styles import card_style
from ..templates import template


def agent_stat_cards() -> rx.Component:
    """Agent metric cards."""
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
                    rx.text("代理总数", size="2", color=rx.color("gray", 11)),
                    rx.text(AgentState.total_agents.to(str), size="6", weight="bold"),
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
                    rx.icon("circle-check", size=24, color=rx.color("green", 11)),
                    padding="12px",
                    background=rx.color("green", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("已启用代理", size="2", color=rx.color("gray", 11)),
                    rx.text(AgentState.active_agents.to(str), size="6", weight="bold"),
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
                    rx.icon("shield-check", size=24, color=rx.color("violet", 11)),
                    padding="12px",
                    background=rx.color("violet", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("已认证代理", size="2", color=rx.color("gray", 11)),
                    rx.text(AgentState.verified_agents.to(str), size="6", weight="bold"),
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
                    rx.text("累计代理利润", size="2", color=rx.color("gray", 11)),
                    rx.text("$", AgentState.total_agent_profit.to(str), size="6", weight="bold"),
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


def agent_status_badge(agent: dict) -> rx.Component:
    return rx.cond(
        agent["is_active"],
        rx.badge("启用中", color_scheme="green"),
        rx.badge("已停用", color_scheme="gray"),
    )


def agent_verify_badge(agent: dict) -> rx.Component:
    return rx.cond(
        agent["is_verified"],
        rx.badge("已认证", color_scheme="blue"),
        rx.badge("待认证", color_scheme="orange"),
    )


def render_agent_row(agent: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(agent["name"], size="2", weight="medium"),
                rx.text(
                    rx.cond(agent["contact_telegram"], agent["contact_telegram"], "-"),
                    size="1",
                    color=rx.color("gray", 10),
                ),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(agent["bot_name"], size="2"),
                rx.code(agent["masked_token"], size="1"),
                align="start",
                spacing="1",
            )
        ),
        rx.table.cell(
            rx.text(
                agent["profit_rate_label"],
                size="2",
                weight="medium",
            )
        ),
        rx.table.cell(
            rx.code(
                rx.cond(agent["usdt_address"], agent["usdt_address"], "-"),
                size="1",
            )
        ),
        rx.table.cell(agent_status_badge(agent)),
        rx.table.cell(agent_verify_badge(agent)),
        rx.table.cell(
            rx.text(
                "Bot ",
                agent["total_bots"].to(str),
                " / 用户 ",
                agent["total_users"].to(str),
                " / 订单 ",
                agent["total_orders"].to(str),
                size="2",
                color=rx.color("gray", 11),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("pencil", size=14),
                        variant="ghost",
                        size="1",
                        on_click=lambda: with_focus_blur(AgentState.open_edit_modal(agent["id"])),
                    ),
                    content="编辑代理配置",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.cond(
                            agent["is_active"],
                            rx.icon("ban", size=14),
                            rx.icon("check", size=14),
                        ),
                        variant="ghost",
                        size="1",
                        color_scheme=rx.cond(agent["is_active"], "red", "green"),
                        on_click=lambda: AgentState.toggle_agent_status(agent["id"]),
                    ),
                    content=rx.cond(agent["is_active"], "停用代理", "启用代理"),
                ),
                spacing="1",
            )
        ),
    )


def agent_list_table() -> rx.Component:
    """Agent table."""
    return rx.box(
        rx.hstack(
            rx.text(
                "共 ",
                AgentState.filtered_agents.length().to(str),
                " 条代理记录",
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
                    rx.table.column_header_cell("代理信息"),
                    rx.table.column_header_cell("Bot 绑定"),
                    rx.table.column_header_cell("分润比例"),
                    rx.table.column_header_cell("USDT 地址"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("认证"),
                    rx.table.column_header_cell("业务数据"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    AgentState.filtered_agents.length() > 0,
                    rx.foreach(AgentState.filtered_agents, render_agent_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无代理数据", size="2", color=rx.color("gray", 10)),
                            col_span=8,
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


def agent_create_modal() -> rx.Component:
    """Create-agent dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("创建代理"),
            rx.dialog.description(
                "创建代理账号并分配 Bot Token、分润比例与收款地址",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.grid(
                    rx.vstack(
                        rx.text("代理名称", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_name,
                            on_change=AgentState.set_create_name,
                            placeholder="例如：代理商D",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Bot 名称", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_bot_name,
                            on_change=AgentState.set_create_bot_name,
                            placeholder="例如：代理D Bot",
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
                rx.grid(
                    rx.vstack(
                        rx.text("Telegram 联系方式", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_contact_telegram,
                            on_change=AgentState.set_create_contact_telegram,
                            placeholder="@agent_d",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("邮箱", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_contact_email,
                            on_change=AgentState.set_create_contact_email,
                            placeholder="agent-d@example.com",
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
                rx.vstack(
                    rx.text("Bot Token", size="2", weight="medium"),
                    rx.input(
                        value=AgentState.create_bot_token,
                        on_change=AgentState.set_create_bot_token,
                        placeholder="123456789:AA...",
                        width="100%",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("分润比例", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_profit_rate,
                            on_change=AgentState.set_create_profit_rate,
                            placeholder="0.12 或 12",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("USDT 地址", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.create_usdt_address,
                            on_change=AgentState.set_create_usdt_address,
                            placeholder="TX...",
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
                        on_click=AgentState.close_create_modal,
                    )
                ),
                rx.spacer(),
                rx.button("创建代理", on_click=AgentState.save_new_agent),
                width="100%",
                margin_top="20px",
            ),
            max_width="620px",
        ),
        open=AgentState.show_create_modal,
        on_open_change=AgentState.handle_create_modal_change,
    )


def agent_edit_modal() -> rx.Component:
    """Edit-agent dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("编辑代理配置"),
            rx.dialog.description(
                "更新代理分润规则、Bot Token 与 USDT 地址",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.grid(
                    rx.vstack(
                        rx.text("代理名称", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_name,
                            on_change=AgentState.set_edit_name,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Bot 名称", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_bot_name,
                            on_change=AgentState.set_edit_bot_name,
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
                rx.grid(
                    rx.vstack(
                        rx.text("Telegram 联系方式", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_contact_telegram,
                            on_change=AgentState.set_edit_contact_telegram,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("邮箱", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_contact_email,
                            on_change=AgentState.set_edit_contact_email,
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
                rx.vstack(
                    rx.text("Bot Token", size="2", weight="medium"),
                    rx.input(
                        value=AgentState.edit_bot_token,
                        on_change=AgentState.set_edit_bot_token,
                        width="100%",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("分润比例", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_profit_rate,
                            on_change=AgentState.set_edit_profit_rate,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("USDT 地址", size="2", weight="medium"),
                        rx.input(
                            value=AgentState.edit_usdt_address,
                            on_change=AgentState.set_edit_usdt_address,
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
                rx.checkbox(
                    "已完成实名认证",
                    checked=AgentState.edit_is_verified,
                    on_change=AgentState.set_edit_is_verified,
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
                        on_click=AgentState.close_edit_modal,
                    )
                ),
                rx.spacer(),
                rx.button("保存配置", on_click=AgentState.save_edit_agent),
                width="100%",
                margin_top="20px",
            ),
            max_width="620px",
        ),
        open=AgentState.show_edit_modal,
        on_open_change=AgentState.handle_edit_modal_change,
    )


def super_admin_only_notice() -> rx.Component:
    return rx.box(
        rx.callout(
            "仅超级管理员可访问代理管理",
            icon="shield-alert",
            color_scheme="orange",
            width="100%",
        ),
        **card_style,
        width="100%",
    )


@template
def agents_page() -> rx.Component:
    """Agents page."""
    return rx.cond(
        AuthState.is_super_admin,
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.heading("代理管理", size="6"),
                    rx.text(
                        "创建代理账号，分配 Bot Token，设置分润规则与收款地址",
                        color=rx.color("gray", 11),
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        "刷新",
                        variant="soft",
                        on_click=AgentState.refresh_list,
                    ),
                    rx.button(
                        rx.icon("plus", size=16),
                        "创建代理",
                        on_click=with_focus_blur(AgentState.open_create_modal),
                    ),
                    spacing="2",
                ),
                width="100%",
                margin_bottom="24px",
            ),
            agent_stat_cards(),
            rx.box(height="24px"),
            rx.box(
                rx.hstack(
                    rx.input(
                        placeholder="搜索代理名称 / Telegram / 邮箱 / Bot...",
                        value=AgentState.search_query,
                        on_change=AgentState.set_search_query,
                        width="320px",
                    ),
                    rx.select(
                        AgentState.status_options,
                        value=AgentState.filter_status,
                        on_change=AgentState.set_filter_status,
                        width="180px",
                    ),
                    width="100%",
                    spacing="3",
                ),
                **card_style,
                width="100%",
                margin_bottom="16px",
            ),
            agent_list_table(),
            agent_create_modal(),
            agent_edit_modal(),
            width="100%",
            on_mount=AgentState.load_agents_data,
        ),
        super_admin_only_notice(),
    )
