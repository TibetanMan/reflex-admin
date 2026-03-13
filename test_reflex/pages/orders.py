"""订单管理页面"""

import reflex as rx
from ..state.auth import AuthState
from ..components.a11y import with_focus_blur
from ..state.order_state import OrderState, Order, OrderItem
from ..styles import card_style
from ..templates import template

ORDER_EXPORT_AUTO_POLL_SCRIPT = """
if (window.__orderExportAutoPollTimer) {
  clearInterval(window.__orderExportAutoPollTimer);
}
var trigger = document.getElementById("order-export-auto-poll-trigger");
if (trigger) {
  trigger.click();
}
window.__orderExportAutoPollTimer = window.setInterval(function () {
  var pollTrigger = document.getElementById("order-export-auto-poll-trigger");
  if (!pollTrigger) {
    clearInterval(window.__orderExportAutoPollTimer);
    window.__orderExportAutoPollTimer = null;
    return;
  }
  pollTrigger.click();
}, 5000);
"""


def order_stat_cards() -> rx.Component:
    """订单统计卡片"""
    return rx.grid(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("shopping_cart", size=24, color=rx.color("blue", 11)),
                    padding="12px",
                    background=rx.color("blue", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总订单", size="2", color=rx.color("gray", 11)),
                    rx.text(OrderState.total_orders, size="6", weight="bold"),
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
                    rx.icon("circle_check", size=24, color=rx.color("green", 11)),
                    padding="12px",
                    background=rx.color("green", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("已完成", size="2", color=rx.color("gray", 11)),
                    rx.text(OrderState.completed_orders, size="6", weight="bold"),
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
                    rx.text("待处理", size="2", color=rx.color("gray", 11)),
                    rx.text(OrderState.pending_orders, size="6", weight="bold"),
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
                    rx.icon("dollar_sign", size=24, color=rx.color("violet", 11)),
                    padding="12px",
                    background=rx.color("violet", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("总收益", size="2", color=rx.color("gray", 11)),
                    rx.text(
                        "$" + OrderState.total_revenue.to(str),
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


def filter_section() -> rx.Component:
    """筛选区域"""
    return rx.box(
        rx.hstack(
            # 搜索框
            rx.input(
                placeholder="搜索订单号或用户...",
                value=OrderState.search_query,
                on_change=OrderState.set_search_query,
                width="280px",
            ),
            # 状态筛选 - 动态选项
            rx.select(
                OrderState.status_options,
                value=OrderState.filter_status,
                on_change=OrderState.set_filter_status,
            ),
            # Bot 筛选 - 动态渲染
            rx.select(
                OrderState.bot_filter_options,
                value=OrderState.filter_bot,
                on_change=OrderState.set_filter_bot,
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh_cw", size=16),
                "刷新",
                variant="soft",
                on_click=OrderState.refresh_list,
            ),
            width="100%",
            spacing="3",
        ),
        **card_style,
        width="100%",
        margin_bottom="16px",
    )


def status_badge(order: Order) -> rx.Component:
    """状态徽章"""
    return rx.match(
        order.status,
        ("completed", rx.badge("已完成", color_scheme="green")),
        ("pending", rx.badge("待处理", color_scheme="orange")),
        ("refunded", rx.badge("已退款", color_scheme="red")),
        ("cancelled", rx.badge("已取消", color_scheme="gray")),
        rx.badge("未知", color_scheme="gray"),
    )


def action_buttons(order: Order) -> rx.Component:
    """操作按钮 - 根据状态显示不同按钮"""
    return rx.hstack(
        # 查看详情按钮 - 所有状态都显示
        rx.tooltip(
            rx.icon_button(
                rx.icon("eye", size=14),
                variant="ghost",
                size="1",
                on_click=lambda: with_focus_blur(OrderState.open_detail_modal(order.id)),
            ),
            content="查看详情",
        ),
        # 刷新按钮 - 仅待处理状态显示
        rx.cond(
            order.status == "pending",
            rx.tooltip(
                rx.icon_button(
                    rx.icon("refresh_cw", size=14),
                    variant="ghost",
                    size="1",
                    color_scheme="blue",
                    on_click=lambda: OrderState.refresh_order(order.id),
                ),
                content="刷新状态",
            ),
        ),
        # 退款按钮 - 除了已退款和已取消状态外都显示
        rx.cond(
            (order.status != "refunded") & (order.status != "cancelled"),
            rx.tooltip(
                rx.icon_button(
                    rx.icon("rotate_ccw", size=14),
                    variant="ghost",
                    size="1",
                    color_scheme="red",
                    on_click=lambda: with_focus_blur(OrderState.open_refund_modal(order.id)),
                ),
                content="退款",
            ),
        ),
        spacing="1",
    )


def render_order_row(order: Order) -> rx.Component:
    """渲染单行订单数据"""
    return rx.table.row(
        rx.table.cell(rx.code(order.order_no, size="1")),
        rx.table.cell(rx.text(order.user, size="2")),
        rx.table.cell(rx.text(order.bot, size="2")),
        rx.table.cell(rx.text(order.item_count, size="2")),
        rx.table.cell(rx.text(f"${order.amount}", size="2", weight="medium")),
        rx.table.cell(status_badge(order)),
        rx.table.cell(rx.text(order.created_at, size="2", color=rx.color("gray", 11))),
        rx.table.cell(action_buttons(order)),
    )


def order_list_table() -> rx.Component:
    """订单列表表格"""
    return rx.box(
        # 表头信息
        rx.hstack(
            rx.text(
                f"共 {OrderState.display_total} 条数据",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            # 排序选择
            rx.hstack(
                rx.text("排序:", size="2", color=rx.color("gray", 11)),
                rx.select(
                    ["最新优先", "最早优先"],
                    default_value="最新优先",
                    on_change=OrderState.set_sort_order,
                    size="1",
                ),
                spacing="2",
                align="center",
            ),
            margin_bottom="12px",
        ),
        
        # 表格
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("订单号"),
                    rx.table.column_header_cell("用户"),
                    rx.table.column_header_cell("Bot"),
                    rx.table.column_header_cell("商品数"),
                    rx.table.column_header_cell("金额"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("创建时间"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    OrderState.paginated_orders,
                    render_order_row,
                ),
            ),
            width="100%",
        ),
        
        # 分页控件
        rx.hstack(
            # 左侧: 显示范围
            rx.text(
                f"显示 {OrderState.display_range} / {OrderState.display_total}",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            # 每页数量选择
            rx.hstack(
                rx.text("每页:", size="2", color=rx.color("gray", 11)),
                rx.select(
                    ["20", "30", "40", "50"],
                    default_value="20",
                    on_change=OrderState.set_page_size,
                    size="1",
                ),
                spacing="2",
                align="center",
            ),
            # 分页按钮
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=14),
                    size="1",
                    variant="soft",
                    on_click=OrderState.first_page,
                    disabled=OrderState.current_page <= 1,
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=14),
                    size="1",
                    variant="soft",
                    on_click=OrderState.prev_page,
                    disabled=OrderState.current_page <= 1,
                ),
                rx.text(
                    f"{OrderState.current_page} / {OrderState.total_pages}",
                    size="2",
                    width="80px",
                    text_align="center",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=OrderState.next_page,
                    disabled=OrderState.current_page >= OrderState.total_pages,
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=OrderState.last_page,
                    disabled=OrderState.current_page >= OrderState.total_pages,
                ),
                spacing="1",
                align="center",
            ),
            margin_top="16px",
            width="100%",
        ),
        
        **card_style,
        width="100%",
    )


def render_order_item_row(item: OrderItem) -> rx.Component:
    """渲染订单商品详情行"""
    return rx.table.row(
        rx.table.cell(
            rx.text(item.name, size="2", weight="medium"),
            style={"text_align": "center"},
        ),
        rx.table.cell(
            rx.badge(item.category, variant="soft"),
            style={"text_align": "center"},
        ),
        rx.table.cell(
            rx.text(item.merchant, size="2"),
            style={"text_align": "center"},
        ),
        rx.table.cell(
            rx.text(item.quantity, size="2"),
            style={"text_align": "center"},
        ),
        rx.table.cell(
            rx.text(f"${item.unit_price}", size="2"),
            style={"text_align": "center"},
        ),
        rx.table.cell(
            rx.text(f"${item.subtotal}", size="2", weight="medium", color=rx.color("green", 11)),
            style={"text_align": "center"},
        ),
    )


def order_detail_modal() -> rx.Component:
    """订单详情弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("订单详情"),
            rx.dialog.description(
                "查看订单详情、用户信息和购买内容。",
                size="2",
                color=rx.color("gray", 11),
            ),
            # 标题栏
            rx.hstack(
                rx.hstack(
                    rx.icon("file_text", size=20, color=rx.color("blue", 11)),
                    rx.text("订单详情", size="5", weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("x", size=16),
                    size="1",
                    variant="ghost",
                    on_click=OrderState.close_detail_modal,
                ),
                width="100%",
                margin_bottom="16px",
            ),
            
            rx.scroll_area(
                rx.vstack(
                    # 订单基本信息
                    rx.box(
                        rx.hstack(
                            rx.icon("receipt", size=16, color=rx.color("blue", 11)),
                            rx.text("订单信息", size="2", weight="bold"),
                            spacing="2",
                            align="center",
                        ),
                        rx.separator(margin_y="12px"),
                        rx.grid(
                            # 订单号
                            rx.box(
                                rx.text("订单号", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.code(OrderState.selected_order_no, size="2"),
                                text_align="center",
                            ),
                            # 创建时间
                            rx.box(
                                rx.text("创建时间", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.text(OrderState.selected_order_created_at, size="2"),
                                text_align="center",
                            ),
                            # 订单金额
                            rx.box(
                                rx.text("订单金额", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.text(
                                    "$" + OrderState.selected_order_amount.to(str),
                                    size="3",
                                    weight="bold",
                                    color=rx.color("green", 11),
                                ),
                                text_align="center",
                            ),
                            # 状态
                            rx.box(
                                rx.text("状态", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.match(
                                    OrderState.selected_order_status,
                                    ("completed", rx.badge("已完成", color_scheme="green", size="2")),
                                    ("pending", rx.badge("待处理", color_scheme="orange", size="2")),
                                    ("refunded", rx.badge("已退款", color_scheme="red", size="2")),
                                    ("cancelled", rx.badge("已取消", color_scheme="gray", size="2")),
                                    rx.badge("未知", color_scheme="gray", size="2"),
                                ),
                                text_align="center",
                            ),
                            columns="4",
                            spacing="4",
                            width="100%",
                        ),
                        background=rx.color("gray", 2),
                        padding="16px",
                        border_radius="12px",
                        width="100%",
                    ),
                    
                    # 用户信息
                    rx.box(
                        rx.hstack(
                            rx.icon("user", size=16, color=rx.color("violet", 11)),
                            rx.text("用户信息", size="2", weight="bold"),
                            spacing="2",
                            align="center",
                        ),
                        rx.separator(margin_y="12px"),
                        rx.grid(
                            # 用户
                            rx.box(
                                rx.text("用户", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.text(OrderState.selected_order_user, size="2", weight="medium"),
                                text_align="center",
                            ),
                            # Telegram ID
                            rx.box(
                                rx.text("Telegram ID", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.code(OrderState.selected_order_telegram_id, size="2"),
                                text_align="center",
                            ),
                            # 来源 Bot
                            rx.box(
                                rx.text("来源 Bot", size="1", color=rx.color("gray", 11), margin_bottom="4px"),
                                rx.badge(OrderState.selected_order_bot, variant="soft", color_scheme="blue"),
                                text_align="center",
                            ),
                            columns="3",
                            spacing="4",
                            width="100%",
                        ),
                        background=rx.color("gray", 2),
                        padding="16px",
                        border_radius="12px",
                        width="100%",
                    ),
                    
                    # 购买内容
                    rx.box(
                        rx.hstack(
                            rx.icon("shopping_bag", size=16, color=rx.color("green", 11)),
                            rx.text("购买内容", size="2", weight="bold"),
                            spacing="2",
                            align="center",
                        ),
                        rx.separator(margin_y="12px"),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("库名称", style={"text_align": "center"}),
                                    rx.table.column_header_cell("分类", style={"text_align": "center"}),
                                    rx.table.column_header_cell("商家", style={"text_align": "center"}),
                                    rx.table.column_header_cell("数量", style={"text_align": "center"}),
                                    rx.table.column_header_cell("单价", style={"text_align": "center"}),
                                    rx.table.column_header_cell("小计", style={"text_align": "center"}),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    OrderState.selected_order_items,
                                    render_order_item_row,
                                ),
                            ),
                            width="100%",
                            size="1",
                        ),
                        background=rx.color("gray", 2),
                        padding="16px",
                        border_radius="12px",
                        width="100%",
                    ),
                    
                    width="100%",
                    spacing="4",
                ),
                max_height="55vh",
                scrollbars="vertical",
            ),
            
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        rx.icon("x", size=14),
                        "关闭",
                        variant="soft",
                        color_scheme="gray",
                        on_click=OrderState.close_detail_modal,
                    ),
                ),
                width="100%",
                margin_top="20px",
            ),
            
            max_width="750px",
            padding="24px",
        ),
        open=OrderState.show_detail_modal,
        on_open_change=OrderState.handle_detail_modal_change,
    )



def refund_modal() -> rx.Component:
    """退款弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("退款确认"),
            rx.dialog.description(
                "确定要为此订单办理退款吗？",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.callout(
                    "退款后商品将标记为无效，金额将返还至用户余额",
                    icon="triangle_alert",
                    color_scheme="orange",
                    width="100%",
                ),
                rx.text("退款原因", size="2", weight="medium"),
                rx.text_area(
                    placeholder="请输入退款原因...",
                    value=OrderState.refund_reason,
                    on_change=OrderState.set_refund_reason,
                    width="100%",
                    rows="3",
                ),
                spacing="3",
                width="100%",
                margin_top="16px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button("取消", variant="soft", color_scheme="gray"),
                ),
                rx.spacer(),
                rx.button(
                    "确认退款",
                    color_scheme="red",
                    on_click=OrderState.process_refund(AuthState.username),
                ),
                width="100%",
                margin_top="24px",
            ),
            max_width="450px",
        ),
        open=OrderState.show_refund_modal,
        on_open_change=OrderState.handle_refund_modal_change,
    )


def export_modal() -> rx.Component:
    """导出订单弹窗"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("download", size=20),
                    rx.text("导出订单"),
                    spacing="2",
                ),
            ),
            rx.dialog.description(
                "选择要导出的 Bot 和日期范围",
                size="2",
                color=rx.color("gray", 11),
            ),
            
            rx.vstack(
                # Bot 选择
                rx.vstack(
                    rx.text("选择 Bot", size="2", weight="medium"),
                    rx.select(
                        OrderState.export_bot_options,
                        placeholder="请选择 Bot",
                        value=OrderState.export_bot,
                        on_change=OrderState.set_export_bot,
                        disabled=OrderState.is_exporting,
                        width="100%",
                    ),
                    align="start",
                    spacing="1",
                    width="100%",
                ),
                
                # 日期范围
                rx.grid(
                    rx.vstack(
                        rx.text("开始日期", size="2", weight="medium"),
                        rx.input(
                            type="date",
                            value=OrderState.export_date_from,
                            on_change=OrderState.set_export_date_from,
                            disabled=OrderState.is_exporting,
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
                            value=OrderState.export_date_to,
                            on_change=OrderState.set_export_date_to,
                            disabled=OrderState.is_exporting,
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
                    "导出将生成包含所选 Bot 在指定日期范围内所有订单的 CSV 文件",
                    icon="info",
                    color_scheme="blue",
                    width="100%",
                ),
                rx.cond(
                    OrderState.is_exporting,
                    rx.vstack(
                        rx.progress(value=OrderState.export_progress, width="100%"),
                        rx.hstack(
                            rx.text(OrderState.export_message, size="2", color=rx.color("gray", 11)),
                            rx.spacer(),
                            rx.text(OrderState.export_record_progress_text, size="2", color=rx.color("gray", 11)),
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                rx.cond(
                    OrderState.export_can_download,
                    rx.callout(
                        OrderState.export_message,
                        icon="circle_check",
                        color_scheme="green",
                        width="100%",
                    ),
                ),
                rx.cond(
                    OrderState.export_is_failed,
                    rx.callout(
                        OrderState.export_message,
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
                    OrderState.export_can_download,
                    rx.button(
                        rx.icon("download", size=16),
                        "Download",
                        variant="soft",
                        color_scheme="green",
                        on_click=OrderState.download_export_file,
                    ),
                ),
                rx.button(
                    rx.icon("download", size=16),
                    "开始导出",
                    on_click=OrderState.export_orders,
                    loading=OrderState.is_exporting,
                    disabled=OrderState.is_exporting,
                ),
                width="100%",
                margin_top="24px",
            ),
            
            max_width="500px",
        ),
        open=OrderState.show_export_modal,
        on_open_change=OrderState.handle_export_modal_change,
    )


def render_recent_order_export_row(task: dict) -> rx.Component:
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
                    on_click=lambda: OrderState.download_export_task_by_id(task["id"]),
                ),
                rx.text("-", size="2", color=rx.color("gray", 10)),
            )
        ),
    )


def recent_order_export_tasks_section() -> rx.Component:
    return rx.box(
        rx.button(
            "",
            id="order-export-auto-poll-trigger",
            on_click=OrderState.poll_export_task_status,
            style={"display": "none"},
        ),
        rx.hstack(
            rx.heading("Recent Export Tasks", size="4"),
            rx.spacer(),
            rx.button(
                rx.icon("refresh_cw", size=14),
                "Refresh",
                size="1",
                variant="soft",
                on_click=OrderState.poll_export_task_status,
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
                    OrderState.recent_export_tasks.length() > 0,
                    rx.foreach(OrderState.recent_export_tasks, render_recent_order_export_row),
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
def orders_page() -> rx.Component:
    """订单管理页面"""
    return rx.box(
        # 页面标题
        rx.hstack(
            rx.vstack(
                rx.heading("订单管理", size="6"),
                rx.text("查看和管理所有订单", color=rx.color("gray", 11)),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=16),
                "导出订单",
                variant="outline",
                on_click=with_focus_blur(OrderState.open_export_modal),
            ),
            width="100%",
            margin_bottom="24px",
        ),
        
        # 统计卡片
        order_stat_cards(),
        
        rx.box(height="24px"),
        
        # 筛选栏
        filter_section(),
        
        # 订单列表
        order_list_table(),
        recent_order_export_tasks_section(),
        
        # 弹窗
        order_detail_modal(),
        refund_modal(),
        export_modal(),
        
        width="100%",
        on_mount=[OrderState.load_orders_data, rx.call_script(ORDER_EXPORT_AUTO_POLL_SCRIPT)],
    )
