"""库存管理页面"""

import reflex as rx
from ..components.a11y import with_focus_blur
from ..state.auth import AuthState
from ..state.inventory import InventoryState, InventoryItem
from ..styles import card_style
from ..templates import template

INVENTORY_UPLOAD_ACCEPT = {
    "text/plain": [".txt"],
    "text/csv": [".csv"],
}


def filter_section() -> rx.Component:
    """筛选区域 - 搜索(商家/ID) + 筛选(商家/状态) + 操作按钮"""
    return rx.box(
        rx.hstack(
            # 搜索框
            rx.input(
                placeholder="搜索商家或ID...",
                value=InventoryState.search_query,
                on_change=InventoryState.set_search_query,
                width="250px",
            ),
            # 商家筛选
            rx.select(
                InventoryState.merchant_filter_options,
                placeholder="筛选商家",
                on_change=InventoryState.set_filter_merchant,
            ),
            # 状态筛选
            rx.select(
                InventoryState.status_options,
                placeholder="筛选状态",
                on_change=InventoryState.set_filter_status,
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=16),
                "刷新",
                variant="soft",
                on_click=InventoryState.refresh_list,
            ),
            rx.button(
                rx.icon("upload", size=16),
                "导入库存",
                on_click=with_focus_blur(InventoryState.open_import_modal),
            ),
            width="100%",
            spacing="3",
        ),
        **card_style,
        width="100%",
        margin_bottom="16px",
    )


def sale_progress_bar(item: InventoryItem) -> rx.Component:
    """售出比进度条"""
    return rx.vstack(
        rx.hstack(
            rx.text(
                item.sold,
                size="1",
                weight="medium",
                color=rx.color("green", 11),
            ),
            rx.text("/", size="1", color=rx.color("gray", 9)),
            rx.text(
                item.total,
                size="1",
                color=rx.color("gray", 11),
            ),
            spacing="1",
        ),
        rx.progress(
            value=rx.cond(
                item.total > 0,
                (item.sold * 100 / item.total).to(int),
                0,
            ),
            width="80px",
            height="6px",
        ),
        rx.hstack(
            rx.text("剩余 ", size="1", color=rx.color("gray", 9)),
            rx.text(item.remaining, size="1", color=rx.color("gray", 9)),
            spacing="0",
        ),
        align="start",
        spacing="1",
    )


def status_badge(item: InventoryItem) -> rx.Component:
    """状态徽章"""
    return rx.cond(
        item.status == "active",
        rx.badge("可售", color_scheme="green"),
        rx.badge("停售", color_scheme="gray"),
    )


def bot_enabled_badge(item: InventoryItem) -> rx.Component:
    return rx.cond(
        item.bot_enabled,
        rx.badge("Bot可售", color_scheme="blue", variant="soft"),
        rx.badge("Bot隐藏", color_scheme="gray", variant="soft"),
    )


def action_buttons(item: InventoryItem) -> rx.Component:
    """操作按钮"""
    return rx.hstack(
        # 更改价格
        rx.tooltip(
            rx.icon_button(
                rx.icon("dollar-sign", size=14),
                size="1",
                variant="soft",
                on_click=lambda: with_focus_blur(InventoryState.open_price_modal(item.id)),
            ),
            content=f"当前: ${item.unit_price} / 挑头${item.pick_price}",
        ),
        # 切换状态
        rx.tooltip(
            rx.icon_button(
                rx.cond(
                    item.status == "active",
                    rx.icon("pause", size=14),
                    rx.icon("play", size=14),
                ),
                size="1",
                variant="soft",
                color_scheme=rx.cond(item.status == "active", "orange", "green"),
                on_click=lambda: InventoryState.toggle_status(item.id, AuthState.username),
            ),
            content=rx.cond(item.status == "active", "停售", "启用"),
        ),
        # 删除
        rx.tooltip(
            rx.icon_button(
                rx.icon("trash-2", size=14),
                size="1",
                variant="soft",
                color_scheme="red",
                on_click=lambda: with_focus_blur(InventoryState.open_delete_modal(item.id)),
            ),
            content="删除",
        ),
        spacing="1",
    )


def render_inventory_row(item: InventoryItem) -> rx.Component:
    """渲染单行库存数据"""
    return rx.table.row(
        rx.table.cell(rx.text(item.id, size="2")),
        rx.table.cell(
            rx.text(item.name, size="2", weight="medium"),
        ),
        rx.table.cell(
            rx.badge(item.category, variant="soft"),
        ),
        rx.table.cell(rx.text(item.merchant, size="2")),
        rx.table.cell(
            rx.text(f"${item.unit_price}", size="2", weight="medium"),
        ),
        rx.table.cell(
            rx.text(f"${item.pick_price}", size="2"),
        ),
        rx.table.cell(status_badge(item)),
        rx.table.cell(bot_enabled_badge(item)),
        rx.table.cell(sale_progress_bar(item)),
        rx.table.cell(
            rx.hstack(
                rx.text(item.created_at[:10], size="1"),
                spacing="1",
            ),
        ),
        rx.table.cell(action_buttons(item)),
    )


def inventory_table() -> rx.Component:
    """库存列表表格"""
    return rx.box(
        # 表头信息
        rx.hstack(
            rx.text(
                f"共 {InventoryState.display_total} 条数据",
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
                    on_change=InventoryState.set_sort_order,
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
                    rx.table.column_header_cell("ID"),
                    rx.table.column_header_cell("库名称"),
                    rx.table.column_header_cell("分类"),
                    rx.table.column_header_cell("商家"),
                    rx.table.column_header_cell("单价"),
                    rx.table.column_header_cell("挑头价"),
                    rx.table.column_header_cell("状态"),
                    rx.table.column_header_cell("Bot可见"),
                    rx.table.column_header_cell("销售情况"),
                    rx.table.column_header_cell("创建时间"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    InventoryState.paginated_items,
                    render_inventory_row,
                ),
            ),
            width="100%",
        ),
        
        # 分页控件
        rx.hstack(
            # 左侧: 显示范围
            rx.text(
                f"显示 {InventoryState.display_range} / {InventoryState.display_total}",
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
                    on_change=InventoryState.set_page_size,
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
                    on_click=InventoryState.first_page,
                    disabled=InventoryState.current_page <= 1,
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=14),
                    size="1",
                    variant="soft",
                    on_click=InventoryState.prev_page,
                    disabled=InventoryState.current_page <= 1,
                ),
                rx.text(
                    f"{InventoryState.current_page} / {InventoryState.total_pages}",
                    size="2",
                    width="80px",
                    text_align="center",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=InventoryState.next_page,
                    disabled=InventoryState.current_page >= InventoryState.total_pages,
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=14),
                    size="1",
                    variant="soft",
                    on_click=InventoryState.last_page,
                    disabled=InventoryState.current_page >= InventoryState.total_pages,
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


def import_modal() -> rx.Component:
    """导入弹窗"""
    return rx.dialog.root(
        rx.dialog.trigger(rx.box()),
        rx.dialog.content(
            rx.dialog.title("导入库存"),
            rx.dialog.description(
                "上传包含商品数据的文本文件，并配置导入参数",
                size="2",
                color=rx.color("gray", 11),
            ),
            
            rx.scroll_area(
                rx.vstack(
                    # 库名称
                    rx.vstack(
                        rx.text("库名称", size="2", weight="medium"),
                        rx.input(
                            placeholder="输入库名称，如: US-VISA-Premium",
                            value=InventoryState.import_name,
                            on_change=InventoryState.set_import_name,
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    
                    # 第一行: 商家绑定 + 分类选择
                    rx.grid(
                        rx.vstack(
                            rx.text("商家绑定", size="2", weight="medium"),
                            rx.select(
                                InventoryState.merchant_names,
                                placeholder="选择商家",
                                value=InventoryState.import_merchant,
                                on_change=InventoryState.set_import_merchant,
                                width="100%",
                            ),
                            align="start",
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("库存分类", size="2", weight="medium"),
                            rx.select(
                                InventoryState.inventory_categories,
                                placeholder="选择分类",
                                value=InventoryState.import_category,
                                on_change=InventoryState.set_import_category,
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
                    
                    # 第二行: 单价 + 挑头价格
                    rx.grid(
                        rx.vstack(
                            rx.text("单价 ($)", size="2", weight="medium"),
                            rx.input(
                                placeholder="输入单价",
                                type="number",
                                value=InventoryState.import_unit_price.to_string(),
                                on_change=InventoryState.set_import_unit_price,
                                width="100%",
                            ),
                            align="start",
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("挑头价格 ($)", size="2", weight="medium"),
                            rx.input(
                                placeholder="输入挑头价格",
                                type="number",
                                value=InventoryState.import_pick_price.to_string(),
                                on_change=InventoryState.set_import_pick_price,
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
                    
                    # 分隔符选择
                    rx.hstack(
                        rx.text("分隔符:", size="2", weight="medium"),
                        rx.radio_group(
                            ["| (竖线)", ": (冒号)", ", (逗号)"],
                            default_value="| (竖线)",
                            on_change=InventoryState.set_delimiter,
                            direction="row",
                        ),
                        width="100%",
                    ),
                    
                    # 文件上传
                    rx.upload(
                        rx.vstack(
                            rx.icon("cloud_upload", size=40, color=rx.color("gray", 8)),
                            rx.text("拖放文件到此处或点击上传", size="2"),
                            rx.text("支持 .txt, .csv 格式", size="1", color=rx.color("gray", 11)),
                            align="center",
                            spacing="2",
                        ),
                        id="inventory_upload",
                        accept=INVENTORY_UPLOAD_ACCEPT,
                        max_files=1,
                        border=f"2px dashed {rx.color('gray', 6)}",
                        border_radius="12px",
                        padding="24px",
                        width="100%",
                        on_drop=InventoryState.handle_file_upload(rx.upload_files(upload_id="inventory_upload")),
                    ),
                    
                    # 推送广告选项
                    rx.box(
                        rx.hstack(
                            rx.switch(
                                checked=InventoryState.import_push_ad,
                                on_change=InventoryState.set_import_push_ad,
                            ),
                            rx.vstack(
                                rx.text("推送广告", size="2", weight="medium"),
                                rx.text("导入完成后是否推送广告通知", size="1", color=rx.color("gray", 11)),
                                align="start",
                                spacing="0",
                            ),
                            spacing="3",
                            align="center",
                        ),
                        width="100%",
                        padding="12px",
                        background=rx.color("gray", 2),
                        border_radius="8px",
                    ),
                    
                    # 预览区域
                    rx.cond(
                        InventoryState.has_preview,
                        rx.box(
                            rx.text("数据预览 (前5行)", size="2", weight="bold", margin_bottom="8px"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("#"),
                                        rx.table.column_header_cell("原始数据"),
                                        rx.table.column_header_cell("字段数"),
                                        rx.table.column_header_cell("BIN"),
                                    ),
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        InventoryState.preview_data,
                                        lambda item: rx.table.row(
                                            rx.table.cell(item["index"]),
                                            rx.table.cell(rx.code(item["raw"], size="1")),
                                            rx.table.cell(item["fields"]),
                                            rx.table.cell(rx.code(item["bin"])),
                                        ),
                                    ),
                                ),
                                width="100%",
                                size="1",
                            ),
                            background=rx.color("gray", 2),
                            padding="12px",
                            border_radius="8px",
                        ),
                    ),
                    
                    # 导入结果
                    rx.cond(
                        InventoryState.has_import_result,
                        rx.box(
                            rx.text("导入结果", size="2", weight="bold", margin_bottom="8px"),
                            rx.hstack(
                                rx.badge(f"总计: {InventoryState.import_result['total']}", color_scheme="gray"),
                                rx.badge(f"成功: {InventoryState.import_result['success']}", color_scheme="green"),
                                rx.badge(f"重复: {InventoryState.import_result['duplicate']}", color_scheme="orange"),
                                rx.badge(f"无效: {InventoryState.import_result['invalid']}", color_scheme="red"),
                                spacing="2",
                            ),
                            background=rx.color("green", 2),
                            padding="12px",
                            border_radius="8px",
                        ),
                    ),
                    
                    # 进度条
                    rx.cond(
                        InventoryState.is_importing,
                        rx.box(
                            rx.progress(value=InventoryState.import_progress, width="100%"),
                            rx.text(
                                f"导入中... {InventoryState.import_progress}%",
                                size="1",
                                color=rx.color("gray", 11),
                                text_align="center",
                            ),
                        ),
                    ),
                    
                    width="100%",
                    spacing="4",
                ),
                max_height="60vh",
                scrollbars="vertical",
            ),
            
            rx.hstack(
                rx.button(
                    "取消",
                    variant="soft",
                    color_scheme="gray",
                    on_click=InventoryState.close_import_modal,
                ),
                rx.spacer(),
                rx.button(
                    "开始导入",
                    on_click=InventoryState.start_import(AuthState.username),
                    loading=InventoryState.is_importing,
                    disabled=~InventoryState.can_submit_import,
                ),
                width="100%",
                margin_top="16px",
            ),
            
            max_width="650px",
        ),
        open=InventoryState.show_import_modal,
    )


def price_edit_modal() -> rx.Component:
    """价格编辑弹窗 - 带二次确认"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("更改价格"),
            rx.dialog.description(
                f"正在修改「{InventoryState.selected_item_name}」的价格",
                size="2",
            ),
            
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("单价 ($)", size="2", weight="medium"),
                        rx.input(
                            type="number",
                            value=InventoryState.edit_unit_price.to_string(),
                            on_change=InventoryState.set_edit_unit_price,
                            width="100%",
                        ),
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("挑头价格 ($)", size="2", weight="medium"),
                        rx.input(
                            type="number",
                            value=InventoryState.edit_pick_price.to_string(),
                            on_change=InventoryState.set_edit_pick_price,
                            width="100%",
                        ),
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.callout(
                    "确认后价格将立即生效，请仔细核对！",
                    icon="triangle_alert",
                    color="orange",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                margin_y="16px",
            ),
            
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=InventoryState.close_price_modal,
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "确认更改",
                    color_scheme="blue",
                    on_click=InventoryState.update_price(AuthState.username),
                ),
                width="100%",
            ),
        ),
        open=InventoryState.show_price_modal,
        on_open_change=InventoryState.handle_price_modal_change,
    )
def delete_confirm_modal() -> rx.Component:
    """删除确认弹窗"""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(rx.box()),
        rx.alert_dialog.content(
            rx.alert_dialog.title("确认删除"),
            rx.alert_dialog.description(
                f"确定要删除「{InventoryState.selected_item_name}」吗？此操作不可恢复。",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("取消", variant="soft", color_scheme="gray"),
                ),
                rx.spacer(),
                rx.alert_dialog.action(
                    rx.button(
                        "确认删除",
                        color_scheme="red",
                        on_click=InventoryState.delete_item(AuthState.username),
                    ),
                ),
                width="100%",
                margin_top="16px",
            ),
        ),
        open=InventoryState.show_delete_modal,
    )


@template
def inventory_page() -> rx.Component:
    """库存管理页面"""
    return rx.vstack(
        # 页面标题
        rx.hstack(
            rx.vstack(
                rx.heading("库存管理", size="6"),
                rx.text("管理所有库存数据、导入、定价", size="2", color=rx.color("gray", 11)),
                align="start",
            ),
            rx.spacer(),
            width="100%",
            margin_bottom="20px",
        ),
        
        # 筛选区域
        filter_section(),
        
        # 库存列表
        inventory_table(),
        
        # 弹窗
        import_modal(),
        price_edit_modal(),
        delete_confirm_modal(),
        
        width="100%",
        spacing="4",
        on_mount=InventoryState.load_inventory_data,
    )
