"""仪表盘页面"""

import reflex as rx
from ..state import AuthState, DashboardState, InventoryState
from ..styles import COLORS, SIZES, card_style
from ..templates import template


def stat_card(
    title: str,
    value: rx.Var | str,
    icon: str,
    trend: rx.Var | float,
    trend_color: rx.Var | str,
    color: str = "accent",
) -> rx.Component:
    """统计卡片组件"""
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=24, color=rx.color(color, 11)),
                padding="12px",
                background=rx.color(color, 3),
                border_radius="12px",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(title, size="2", color=rx.color("gray", 11)),
                rx.text(value, size="6", weight="bold"),
                align="end",
                spacing="1",
            ),
            width="100%",
            align="center",
        ),
        rx.hstack(
            rx.cond(
                trend >= 0,
                rx.hstack(
                    rx.icon("trending-up", size=16, color=rx.color("green", 11)),
                    rx.text(
                        rx.Var.create(f"+") + trend.to_string() + "%",
                        size="2",
                        color=rx.color("green", 11),
                    ),
                    spacing="1",
                ),
                rx.hstack(
                    rx.icon("trending-down", size=16, color=rx.color("red", 11)),
                    rx.text(
                        trend.to_string() + "%",
                        size="2",
                        color=rx.color("red", 11),
                    ),
                    spacing="1",
                ),
            ),
            rx.text("vs 昨日", size="1", color=rx.color("gray", 9)),
            margin_top="12px",
            spacing="2",
        ),
        **card_style,
        width="100%",
    )


def recent_orders_table() -> rx.Component:
    """最近订单表格"""
    return rx.box(
        rx.hstack(
            rx.text("最近订单", size="4", weight="bold"),
            rx.spacer(),
            rx.link("查看全部", href="/orders", size="2", color=rx.color("accent", 11)),
            width="100%",
            margin_bottom="16px",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("订单号"),
                    rx.table.column_header_cell("用户"),
                    rx.table.column_header_cell("金额"),
                    rx.table.column_header_cell("数量"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("时间"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    DashboardState.recent_orders,
                    lambda order: rx.table.row(
                        rx.table.cell(rx.text(order["id"], size="2")),
                        rx.table.cell(rx.text(order["user"], size="2")),
                        rx.table.cell(
                            rx.text(f"${order['amount']}", size="2", weight="medium")
                        ),
                        rx.table.cell(rx.text(order["items"], size="2")),
                        rx.table.cell(
                            rx.cond(
                                order["status"] == "completed",
                                rx.badge("已完成", color_scheme="green"),
                                rx.cond(
                                    order["status"] == "pending",
                                    rx.badge("待处理", color_scheme="orange"),
                                    rx.badge("已退款", color_scheme="red"),
                                ),
                            ),
                        ),
                        rx.table.cell(
                            rx.text(order["time"], size="2", color=rx.color("gray", 11))
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        **card_style,
        width="100%",
    )


def top_categories_list() -> rx.Component:
    """热门分类列表"""
    return rx.box(
        rx.hstack(
            rx.text("热门分类", size="4", weight="bold"),
            rx.spacer(),
            rx.link("管理分类", href="/inventory", size="2", color=rx.color("accent", 11)),
            width="100%",
            margin_bottom="16px",
        ),
        rx.vstack(
            rx.foreach(
                DashboardState.top_categories,
                lambda cat: rx.box(
                    rx.hstack(
                        rx.text(cat["name"], size="2", weight="medium"),
                        rx.spacer(),
                        rx.text(
                            f"库存: {cat['stock']} | 已售: {cat['sales']}",
                            size="1",
                            color=rx.color("gray", 11),
                        ),
                        width="100%",
                    ),
                    rx.progress(value=cat["progress"], width="100%", height="6px"),
                    width="100%",
                    padding="8px 0",
                ),
            ),
            width="100%",
            spacing="2",
        ),
        **card_style,
        width="100%",
    )


def bot_status_list() -> rx.Component:
    """Bot 状态列表"""
    return rx.box(
        rx.hstack(
            rx.text("Bot 状态", size="4", weight="bold"),
            rx.spacer(),
            rx.link("管理 Bot", href="/bots", size="2", color=rx.color("accent", 11)),
            width="100%",
            margin_bottom="16px",
        ),
        rx.vstack(
            rx.foreach(
                DashboardState.bot_stats,
                lambda bot: rx.hstack(
                    rx.cond(
                        bot["status"] == "active",
                        rx.box(
                            width="8px",
                            height="8px",
                            background=rx.color("green", 9),
                            border_radius="50%",
                        ),
                        rx.box(
                            width="8px",
                            height="8px",
                            background=rx.color("gray", 6),
                            border_radius="50%",
                        ),
                    ),
                    rx.vstack(
                        rx.text(bot["name"], size="2", weight="medium"),
                        rx.text(
                            f"用户: {bot['users']} | 订单: {bot['orders']}",
                            size="1",
                            color=rx.color("gray", 11),
                        ),
                        align="start",
                        spacing="0",
                    ),
                    rx.spacer(),
                    rx.cond(
                        bot["status"] == "active",
                        rx.badge("运行中", color_scheme="green", size="1"),
                        rx.badge("已停止", color_scheme="gray", size="1"),
                    ),
                    width="100%",
                    padding="8px 0",
                    align="center",
                ),
            ),
            width="100%",
            spacing="1",
        ),
        **card_style,
        width="100%",
    )


def recent_deposits_list() -> rx.Component:
    """最近充值列表"""
    return rx.box(
        rx.hstack(
            rx.text("最近充值", size="4", weight="bold"),
            rx.spacer(),
            rx.link("查看全部", href="/finance", size="2", color=rx.color("accent", 11)),
            width="100%",
            margin_bottom="16px",
        ),
        rx.vstack(
            rx.foreach(
                DashboardState.recent_deposits,
                lambda dep: rx.hstack(
                    rx.box(
                        rx.icon("wallet", size=16, color=rx.color("accent", 11)),
                        padding="8px",
                        background=rx.color("accent", 3),
                        border_radius="8px",
                    ),
                    rx.vstack(
                        rx.text(dep["user"], size="2", weight="medium"),
                        rx.text(dep["time"], size="1", color=rx.color("gray", 11)),
                        align="start",
                        spacing="0",
                    ),
                    rx.spacer(),
                    rx.vstack(
                        rx.text(f"+${dep['amount']}", size="2", weight="bold", color=rx.color("green", 11)),
                        rx.cond(
                            dep["status"] == "completed",
                            rx.badge("已完成", color_scheme="green", size="1"),
                            rx.badge("确认中", color_scheme="orange", size="1"),
                        ),
                        align="end",
                        spacing="1",
                    ),
                    width="100%",
                    padding="8px 0",
                    align="center",
                ),
            ),
            width="100%",
            spacing="1",
        ),
        **card_style,
        width="100%",
    )


def quick_actions() -> rx.Component:
    """快捷操作"""
    return rx.box(
        rx.text("快捷操作", size="4", weight="bold", margin_bottom="16px"),
        rx.grid(
            rx.button(
                rx.icon("upload", size=20),
                rx.text("导入库存"),
                variant="soft",
                size="3",
                width="100%",
                on_click=InventoryState.open_import_modal_from_dashboard,
            ),
            rx.button(
                rx.icon("users", size=20),
                rx.text("用户管理"),
                variant="soft",
                size="3",
                width="100%",
                on_click=rx.redirect("/users"),
            ),
            rx.button(
                rx.icon("bot", size=20),
                rx.text("Bot 管理"),
                variant="soft",
                size="3",
                width="100%",
                on_click=rx.redirect("/bots"),
            ),
            rx.button(
                rx.icon("settings", size=20),
                rx.text("系统设置"),
                variant="soft",
                size="3",
                width="100%",
                on_click=rx.redirect("/settings"),
            ),
            columns="2",
            spacing="3",
            width="100%",
        ),
        **card_style,
        width="100%",
    )


@template
def dashboard() -> rx.Component:
    """仪表盘页面"""
    return rx.box(
        # 页面标题
        rx.hstack(
            rx.vstack(
                rx.heading("仪表盘", size="6"),
                rx.text("欢迎回来，查看今日运营数据", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=16),
                "刷新数据",
                variant="soft",
                size="2",
                on_click=DashboardState.refresh_data,
            ),
            width="100%",
            margin_bottom="24px",
        ),
        
        # 统计卡片
        rx.grid(
            stat_card(
                "今日销售额",
                DashboardState.formatted_sales,
                "dollar-sign",
                DashboardState.sales_trend,
                DashboardState.sales_trend_color,
                "green",
            ),
            stat_card(
                "今日订单",
                DashboardState.today_orders.to_string(),
                "shopping-cart",
                DashboardState.orders_trend,
                DashboardState.orders_trend_color,
                "blue",
            ),
            stat_card(
                "新增用户",
                DashboardState.new_users.to_string(),
                "user-plus",
                DashboardState.users_trend,
                DashboardState.users_trend_color,
                "violet",
            ),
            stat_card(
                "库存总数",
                DashboardState.total_stock.to_string(),
                "package",
                DashboardState.stock_trend,
                DashboardState.stock_trend_color,
                "orange",
            ),
            columns="4",
            spacing="4",
            width="100%",
            margin_bottom="24px",
        ),
        
        # 主内容区
        rx.grid(
            # 左侧 - 订单表格
            rx.box(
                recent_orders_table(),
                grid_column="span 2",
            ),
            # 右侧 - 侧边栏
            rx.vstack(
                quick_actions(),
                top_categories_list(),
                spacing="4",
                width="100%",
            ),
            columns="3",
            spacing="4",
            width="100%",
            margin_bottom="24px",
        ),
        
        # 底部区域
        rx.grid(
            bot_status_list(),
            recent_deposits_list(),
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        width="100%",
        on_mount=DashboardState.load_dashboard_data,
    )


# 导出页面
index = dashboard
