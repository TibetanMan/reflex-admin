"""商家管理页面。"""

import reflex as rx

from ..components.a11y import with_focus_blur
from ..state.auth import AuthState
from ..state.merchant_state import MerchantState
from ..styles import card_style
from ..templates import template


def merchant_stat_cards() -> rx.Component:
    """商家 KPI 卡片。"""
    return rx.grid(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("store", size=24, color=rx.color("blue", 11)),
                    padding="12px",
                    background=rx.color("blue", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("商家总数", size="2", color=rx.color("gray", 11)),
                    rx.text(MerchantState.total_merchants.to(str), size="6", weight="bold"),
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
                    rx.text("启用商家", size="2", color=rx.color("gray", 11)),
                    rx.text(MerchantState.active_merchants.to(str), size="6", weight="bold"),
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
                    rx.icon("badge-check", size=24, color=rx.color("violet", 11)),
                    padding="12px",
                    background=rx.color("violet", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("认证商家", size="2", color=rx.color("gray", 11)),
                    rx.text(MerchantState.verified_merchants.to(str), size="6", weight="bold"),
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
                    rx.icon("trending-up", size=24, color=rx.color("orange", 11)),
                    padding="12px",
                    background=rx.color("orange", 3),
                    border_radius="12px",
                ),
                rx.vstack(
                    rx.text("累计销售额", size="2", color=rx.color("gray", 11)),
                    rx.text("$", MerchantState.total_sales_amount.to(str), size="6", weight="bold"),
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


def merchant_status_badge(merchant: dict) -> rx.Component:
    return rx.cond(
        merchant["is_active"],
        rx.badge("已启用", color_scheme="green"),
        rx.badge("已停用", color_scheme="gray"),
    )


def merchant_verify_badge(merchant: dict) -> rx.Component:
    return rx.cond(
        merchant["is_verified"],
        rx.badge("已认证", color_scheme="blue"),
        rx.badge("待审核", color_scheme="orange"),
    )


def merchant_featured_badge(merchant: dict) -> rx.Component:
    return rx.cond(
        merchant["is_featured"],
        rx.badge("推荐", color_scheme="amber"),
        rx.badge("普通", color_scheme="gray"),
    )


def render_merchant_row(merchant: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(merchant["name"], size="2", weight="medium"),
                rx.text(
                    rx.cond(merchant["contact_telegram"], merchant["contact_telegram"], "-"),
                    size="1",
                    color=rx.color("gray", 10),
                ),
                rx.text(
                    rx.cond(merchant["contact_email"], merchant["contact_email"], "-"),
                    size="1",
                    color=rx.color("gray", 10),
                ),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text("服务费率", size="1", color=rx.color("gray", 9)),
                rx.text(merchant["fee_rate_label"], size="2", weight="medium"),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.code(
                rx.cond(merchant["usdt_address"], merchant["usdt_address"], "-"),
                size="1",
            )
        ),
        rx.table.cell(merchant_status_badge(merchant)),
        rx.table.cell(merchant_verify_badge(merchant)),
        rx.table.cell(merchant_featured_badge(merchant)),
        rx.table.cell(
            rx.vstack(
                rx.text(
                    "商品 ",
                    merchant["total_products"].to(str),
                    " / 已售 ",
                    merchant["sold_products"].to(str),
                    size="2",
                ),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text("$", merchant["total_sales"].to(str), size="2", weight="medium"),
                align="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("pencil", size=14),
                        variant="ghost",
                        size="1",
                        on_click=lambda: with_focus_blur(MerchantState.open_edit_modal(merchant["id"])),
                    ),
                    content="编辑配置",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("download", size=14),
                        variant="ghost",
                        size="1",
                        color_scheme="blue",
                        on_click=lambda: MerchantState.export_merchant_orders(merchant["id"]),
                    ),
                    content="导出订单",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.cond(
                            merchant["is_active"],
                            rx.icon("ban", size=14),
                            rx.icon("check", size=14),
                        ),
                        variant="ghost",
                        size="1",
                        color_scheme=rx.cond(merchant["is_active"], "red", "green"),
                        on_click=lambda: MerchantState.toggle_merchant_status(merchant["id"]),
                    ),
                    content=rx.cond(merchant["is_active"], "停用", "启用"),
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.cond(
                            merchant["is_featured"],
                            rx.icon("star-off", size=14),
                            rx.icon("star", size=14),
                        ),
                        variant="ghost",
                        size="1",
                        color_scheme=rx.cond(merchant["is_featured"], "gray", "amber"),
                        on_click=lambda: MerchantState.toggle_merchant_featured(merchant["id"]),
                    ),
                    content=rx.cond(merchant["is_featured"], "取消推荐", "设为推荐"),
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.cond(
                            merchant["is_verified"],
                            rx.icon("shield-x", size=14),
                            rx.icon("shield-check", size=14),
                        ),
                        variant="ghost",
                        size="1",
                        color_scheme=rx.cond(merchant["is_verified"], "orange", "blue"),
                        on_click=lambda: MerchantState.toggle_merchant_verified(merchant["id"]),
                    ),
                    content=rx.cond(merchant["is_verified"], "设为待审核", "通过认证"),
                ),
                spacing="1",
            )
        ),
    )


def merchant_list_table() -> rx.Component:
    """商家表格。"""
    return rx.box(
        rx.hstack(
            rx.text(
                "共 ",
                MerchantState.filtered_merchants.length().to(str),
                " 家商家",
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
                    rx.table.column_header_cell("商家信息"),
                    rx.table.column_header_cell("服务费率"),
                    rx.table.column_header_cell("USDT 地址"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("认证"),
                    rx.table.column_header_cell("推荐"),
                    rx.table.column_header_cell("库存数据"),
                    rx.table.column_header_cell("销售数据"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    MerchantState.filtered_merchants.length() > 0,
                    rx.foreach(MerchantState.filtered_merchants, render_merchant_row),
                    rx.table.row(
                        rx.table.cell(
                            rx.text("暂无商家数据", size="2", color=rx.color("gray", 10)),
                            col_span=9,
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


def merchant_create_modal() -> rx.Component:
    """新建商家弹窗。"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("新建商家"),
            rx.dialog.description(
                "创建商家账号并配置费率与收款地址。",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.input(
                    value=MerchantState.create_name,
                    on_change=MerchantState.set_create_name,
                    placeholder="商家名称",
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.create_fee_rate,
                    on_change=MerchantState.set_create_fee_rate,
                    placeholder="费率：0.05 或 5",
                    width="100%",
                ),
                rx.text_area(
                    value=MerchantState.create_description,
                    on_change=MerchantState.set_create_description,
                    placeholder="商家简介",
                    width="100%",
                    rows="2",
                ),
                rx.input(
                    value=MerchantState.create_contact_telegram,
                    on_change=MerchantState.set_create_contact_telegram,
                    placeholder="@merchant",
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.create_contact_email,
                    on_change=MerchantState.set_create_contact_email,
                    placeholder="merchant@example.com",
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.create_usdt_address,
                    on_change=MerchantState.set_create_usdt_address,
                    placeholder="TX...",
                    width="100%",
                ),
                rx.checkbox(
                    "设为推荐商家",
                    checked=MerchantState.create_is_featured,
                    on_change=MerchantState.set_create_is_featured,
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
                        on_click=MerchantState.close_create_modal,
                    )
                ),
                rx.spacer(),
                rx.button("创建商家", on_click=MerchantState.save_new_merchant),
                width="100%",
                margin_top="20px",
            ),
            max_width="620px",
        ),
        open=MerchantState.show_create_modal,
        on_open_change=MerchantState.handle_create_modal_change,
    )


def merchant_edit_modal() -> rx.Component:
    """编辑商家弹窗。"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("编辑商家"),
            rx.dialog.description(
                "更新商家资料、收款地址与认证状态。",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.vstack(
                rx.input(
                    value=MerchantState.edit_name,
                    on_change=MerchantState.set_edit_name,
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.edit_fee_rate,
                    on_change=MerchantState.set_edit_fee_rate,
                    width="100%",
                ),
                rx.text_area(
                    value=MerchantState.edit_description,
                    on_change=MerchantState.set_edit_description,
                    width="100%",
                    rows="2",
                ),
                rx.input(
                    value=MerchantState.edit_contact_telegram,
                    on_change=MerchantState.set_edit_contact_telegram,
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.edit_contact_email,
                    on_change=MerchantState.set_edit_contact_email,
                    width="100%",
                ),
                rx.input(
                    value=MerchantState.edit_usdt_address,
                    on_change=MerchantState.set_edit_usdt_address,
                    width="100%",
                ),
                rx.checkbox(
                    "已通过认证",
                    checked=MerchantState.edit_is_verified,
                    on_change=MerchantState.set_edit_is_verified,
                ),
                rx.checkbox(
                    "推荐商家",
                    checked=MerchantState.edit_is_featured,
                    on_change=MerchantState.set_edit_is_featured,
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
                        on_click=MerchantState.close_edit_modal,
                    )
                ),
                rx.spacer(),
                rx.button("保存修改", on_click=MerchantState.save_edit_merchant),
                width="100%",
                margin_top="20px",
            ),
            max_width="620px",
        ),
        open=MerchantState.show_edit_modal,
        on_open_change=MerchantState.handle_edit_modal_change,
    )


def super_admin_only_notice() -> rx.Component:
    return rx.box(
        rx.callout(
            "仅超级管理员可访问商家管理页面。",
            icon="shield-alert",
            color_scheme="orange",
            width="100%",
        ),
        **card_style,
        width="100%",
    )


@template
def merchants_page() -> rx.Component:
    """商家管理页。"""
    return rx.cond(
        AuthState.is_super_admin,
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.heading("商家管理", size="6"),
                    rx.text(
                        "统一管理商家入驻、收款配置与经营表现。",
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
                        on_click=MerchantState.refresh_list,
                    ),
                    rx.button(
                        rx.icon("plus", size=16),
                        "新建商家",
                        on_click=with_focus_blur(MerchantState.open_create_modal),
                    ),
                    spacing="2",
                ),
                width="100%",
                margin_bottom="24px",
            ),
            merchant_stat_cards(),
            rx.box(height="24px"),
            rx.box(
                rx.hstack(
                    rx.input(
                        placeholder="搜索商家 / Telegram / 邮箱...",
                        value=MerchantState.search_query,
                        on_change=MerchantState.set_search_query,
                        width="320px",
                    ),
                    rx.select(
                        MerchantState.status_options,
                        value=MerchantState.filter_status,
                        on_change=MerchantState.set_filter_status,
                        width="220px",
                    ),
                    width="100%",
                    spacing="3",
                ),
                **card_style,
                width="100%",
                margin_bottom="16px",
            ),
            merchant_list_table(),
            merchant_create_modal(),
            merchant_edit_modal(),
            width="100%",
            on_mount=MerchantState.load_merchants_data,
        ),
        super_admin_only_notice(),
    )
