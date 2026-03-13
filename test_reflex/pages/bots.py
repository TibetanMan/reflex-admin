"""Bot 管理页面"""

import reflex as rx
from ..components.a11y import with_focus_blur
from ..state.bot_state import BotState
from ..styles import card_style
from ..templates import template


def bot_stat_cards() -> rx.Component:
    """Bot 统计卡片"""
    return rx.grid(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("bot", size=24, color=rx.color("indigo", 11)),
                    padding="12px",
                    background=rx.color("indigo", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("Bot 总数", size="2", color=rx.color("gray", 11)),
                    rx.text(BotState.total_bots, size="6", weight="bold"),
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
                    rx.icon("activity", size=24, color=rx.color("green", 11)),
                    padding="12px",
                    background=rx.color("green", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("运行中", size="2", color=rx.color("gray", 11)),
                    rx.text(BotState.active_bots, size="6", weight="bold"),
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
                    rx.icon("users", size=24, color=rx.color("blue", 11)),
                    padding="12px",
                    background=rx.color("blue", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总用户数", size="2", color=rx.color("gray", 11)),
                    rx.text(BotState.total_bot_users, size="6", weight="bold"),
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
                    rx.icon("dollar_sign", size=24, color=rx.color("orange", 11)),
                    padding="12px",
                    background=rx.color("orange", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总收益", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$" + BotState.total_bot_revenue.to(str),
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


def create_bot_modal() -> rx.Component:
    """创建 Bot 弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("添加新 Bot"),
            rx.dialog.description(
                "输入 Telegram Bot Token 和配置信息",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.text("Bot 名称 *", size="2", weight="medium"),
                rx.input(
                    placeholder="例如: 我的商店 Bot",
                    value=BotState.form_name,
                    on_change=BotState.set_form_name,
                    width="100%",
                ),
                rx.text("Telegram Bot Token *", size="2", weight="medium"),
                rx.input(
                    placeholder="从 @BotFather 获取的 Token",
                    value=BotState.form_token,
                    on_change=BotState.set_form_token,
                    width="100%",
                    type="password",
                ),
                rx.text("归属", size="2", weight="medium"),
                rx.select(
                    BotState.owner_options,
                    value=BotState.form_owner,
                    on_change=BotState.set_form_owner,
                    width="100%",
                ),
                rx.text("USDT 收款地址 (TRC20)", size="2", weight="medium"),
                rx.input(
                    placeholder="TRC20 地址，例如: TXyz123...",
                    value=BotState.form_usdt_address,
                    on_change=BotState.set_form_usdt_address,
                    width="100%",
                ),
                rx.text("欢迎消息 (可选)", size="2", weight="medium"),
                rx.text_area(
                    placeholder="用户首次启动 Bot 时显示的消息",
                    value=BotState.form_welcome_message,
                    on_change=BotState.set_form_welcome_message,
                    width="100%",
                    rows="3",
                ),
                spacing="3",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.button(
                    "取消",
                    variant="soft",
                    color_scheme="gray",
                    on_click=BotState.close_create_modal,
                ),
                rx.spacer(),
                rx.button("创建 Bot", on_click=BotState.create_bot),
                width="100%",
                margin_top="24px",
            ),
            max_width="500px",
        ),
        open=BotState.show_create_modal,
    )


def edit_bot_modal() -> rx.Component:
    """编辑 Bot 弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("编辑 Bot 设置"),
            rx.dialog.description(
                "修改 Bot 配置信息",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.text("Bot 名称", size="2", weight="medium"),
                rx.input(
                    placeholder="Bot 名称",
                    value=BotState.form_name,
                    on_change=BotState.set_form_name,
                    width="100%",
                ),
                rx.text("归属", size="2", weight="medium"),
                rx.select(
                    BotState.owner_options,
                    value=BotState.form_owner,
                    on_change=BotState.set_form_owner,
                    width="100%",
                ),
                rx.text("USDT 收款地址 (TRC20)", size="2", weight="medium"),
                rx.input(
                    placeholder="TRC20 地址，例如: TXyz123...",
                    value=BotState.form_usdt_address,
                    on_change=BotState.set_form_usdt_address,
                    width="100%",
                ),
                rx.text(
                    "收款地址用于接收用户的 USDT 充值",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                spacing="3",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.button(
                    "取消",
                    variant="soft",
                    color_scheme="gray",
                    on_click=BotState.close_edit_modal,
                ),
                rx.spacer(),
                rx.button("保存修改", on_click=BotState.update_bot),
                width="100%",
                margin_top="24px",
            ),
            max_width="450px",
        ),
        open=BotState.show_edit_modal,
    )


def delete_bot_modal() -> rx.Component:
    """删除 Bot 确认弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("确认删除"),
            rx.vstack(
                rx.callout(
                    rx.text(
                        "确定要删除 Bot「" + BotState.selected_bot_name + "」吗？此操作不可撤销。"
                    ),
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                spacing="3",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.button(
                    "取消",
                    variant="soft",
                    color_scheme="gray",
                    on_click=BotState.close_delete_modal,
                ),
                rx.spacer(),
                rx.button(
                    "确认删除",
                    color_scheme="red",
                    on_click=BotState.delete_bot,
                ),
                width="100%",
                margin_top="24px",
            ),
            max_width="400px",
        ),
        open=BotState.show_delete_modal,
    )


def render_bot_row(bot) -> rx.Component:
    """渲染单个 Bot 行 - 使用 BotInfo 类型"""
    # 从 BotInfo 对象获取属性
    bot_id = bot.id
    is_active = bot.status == "active"
    is_runtime_selected = getattr(bot, "runtime_selected", False)
    
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.icon("bot", size=16, color="white"),
                    padding="8px",
                    background=rx.cond(
                        is_active,
                        rx.color("accent", 9),
                        rx.color("gray", 6),
                    ),
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text(bot.name, size="2", weight="medium"),
                    rx.text(bot.token_masked, size="1", color=rx.color("gray", 9)),
                    align="start",
                    spacing="0",
                ),
                spacing="2",
            )
        ),
        rx.table.cell(rx.code(bot.username, size="1")),
        rx.table.cell(
            rx.vstack(
                rx.cond(
                    is_active,
                    rx.badge("运行中", color_scheme="green"),
                    rx.badge("已停止", color_scheme="gray"),
                ),
                rx.cond(
                    is_runtime_selected,
                    rx.badge("当前运行", color_scheme="blue", variant="soft"),
                    rx.box(),
                ),
                align="start",
                spacing="1",
            )
        ),
        rx.table.cell(rx.text(bot.owner, size="2")),
        rx.table.cell(rx.text(bot.users, size="2")),
        rx.table.cell(rx.text(bot.orders, size="2")),
        rx.table.cell(
            rx.text(
                "$" + bot.revenue.to(str),
                size="2",
                weight="medium",
                color=rx.color("green", 11),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("settings", size=14),
                        variant="ghost",
                        size="1",
                        on_click=lambda: with_focus_blur(BotState.open_edit_modal(bot_id)),
                    ),
                    content="编辑设置",
                ),
                rx.tooltip(
                    rx.box(rx.cond(
                        is_active,
                        rx.icon_button(
                            rx.icon("pause", size=14),
                            variant="ghost",
                            size="1",
                            color_scheme="orange",
                            on_click=lambda: BotState.toggle_bot_status(bot_id),
                        ),
                        rx.icon_button(
                            rx.icon("play", size=14),
                            variant="ghost",
                            size="1",
                            color_scheme="green",
                            on_click=lambda: BotState.toggle_bot_status(bot_id),
                        ),
                    )),
                    content=rx.cond(is_active, "暂停运行", "启动运行"),
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("trash_2", size=14),
                        variant="ghost",
                        size="1",
                        color_scheme="red",
                        on_click=lambda: with_focus_blur(BotState.open_delete_modal(bot_id)),
                    ),
                    content="删除",
                ),
                spacing="1",
            )
        ),
    )


def bot_list_table() -> rx.Component:
    """Bot 列表表格 - 动态渲染"""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Bot 名称"),
                    rx.table.column_header_cell("用户名"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("归属"),
                    rx.table.column_header_cell("用户数"),
                    rx.table.column_header_cell("订单数"),
                    rx.table.column_header_cell("收益"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.foreach(BotState.filtered_bots, render_bot_row),
            ),
            width="100%",
        ),
        **card_style,
        width="100%",
    )


@template
def bots_page() -> rx.Component:
    """Bot 管理页面"""
    return rx.box(
        # 页面标题
        rx.hstack(
            rx.vstack(
                rx.heading("Bot 管理", size="6"),
                rx.text("管理 Telegram Bot 实例", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("plus", size=16),
                "添加 Bot",
                on_click=with_focus_blur(BotState.open_create_modal),
            ),
            width="100%",
            margin_bottom="24px",
        ),
        
        # 统计卡片
        bot_stat_cards(),
        
        rx.box(height="24px"),
        
        # 筛选栏
        rx.box(
            rx.hstack(
                rx.input(
                    placeholder="搜索 Bot 名称...",
                    value=BotState.search_query,
                    on_change=BotState.set_search_query,
                    width="250px",
                ),
                rx.select(
                    BotState.status_filter_options,
                    value=BotState.filter_status,
                    on_change=BotState.set_filter_status,
                    default_value="全部状态",
                ),
                rx.select(
                    BotState.owner_filter_options,
                    value=BotState.filter_owner,
                    on_change=BotState.set_filter_owner,
                    default_value="全部归属",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh_cw", size=16),
                    "刷新",
                    variant="soft",
                    on_click=BotState.refresh_list,
                ),
                width="100%",
                spacing="3",
            ),
            **card_style,
            width="100%",
            margin_bottom="16px",
        ),
        
        # Bot 列表
        bot_list_table(),
        
        # 弹窗
        create_bot_modal(),
        edit_bot_modal(),
        delete_bot_modal(),
        
        width="100%",
        on_mount=BotState.load_bots_data,
    )
