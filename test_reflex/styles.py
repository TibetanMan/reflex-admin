"""全局样式配置"""

import reflex as rx

# ==============================
# 颜色配置 (使用 Reflex/Radix 语义化颜色)
# ==============================
# 为了兼容之前的代码，我们保留 COLORS 字典，
# 但将其值更新为 Reflex 主题色变量，以支持明暗模式
COLORS = {
    "primary": rx.color("accent", 9),
    "primary_dark": rx.color("accent", 11),
    "secondary": rx.color("violet", 9),
    "success": rx.color("green", 9),
    "warning": rx.color("orange", 9),
    "danger": rx.color("red", 9),
    "info": rx.color("cyan", 9),
    "gray": {
        "50": rx.color("gray", 1),
        "100": rx.color("gray", 2),
        "200": rx.color("gray", 3),
        "300": rx.color("gray", 4),
        "400": rx.color("gray", 5),
        "500": rx.color("gray", 6),
        "600": rx.color("gray", 8),
        "700": rx.color("gray", 10),
        "800": rx.color("gray", 11),
        "900": rx.color("gray", 12),
    },
}

# ==============================
# 尺寸配置
# ==============================
SIZES = {
    "sidebar_width": "280px",
    "sidebar_collapsed_width": "80px",
    "navbar_height": "64px",
    "border_radius": "12px",
    "border_radius_sm": "8px",
    "border_radius_lg": "16px",
}

# ==============================
# 通用样式
# ==============================
# 卡片样式 - 自动适配背景色
card_style = {
    "background": rx.color("gray", 2),  # 明: 浅灰 / 暗: 深灰
    "border_radius": SIZES["border_radius"],
    "box_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "padding": "24px",
    "border": f"1px solid {rx.color('gray', 4)}",
    "transition": "all 0.3s ease",
    "_hover": {
        "box_shadow": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "transform": "translateY(-2px)",
        "border_color": rx.color("accent", 8),
    },
}

# 按钮样式
button_primary_style = {
    "border_radius": SIZES["border_radius_sm"],
    "padding": "12px 24px",
    "font_weight": "600",
    "cursor": "pointer",
}

# 侧边栏样式
sidebar_style = {
    "position": "fixed",
    "left": "0",
    "top": "0",
    "height": "100vh",
    "width": SIZES["sidebar_width"],
    "background": rx.color("gray", 1),
    "border_right": f"1px solid {rx.color('gray', 4)}",
    "padding": "24px 16px",
    "z_index": "100",
    "transition": "all 0.3s ease",
}

# 侧边栏菜单项样式
sidebar_item_style = {
    "display": "flex",
    "align_items": "center",
    "gap": "12px",
    "padding": "12px 16px",
    "border_radius": SIZES["border_radius_sm"],
    "cursor": "pointer",
    "transition": "all 0.2s ease",
    "color": rx.color("gray", 11),
    "_hover": {
        "background": rx.color("gray", 3),
        "color": rx.color("accent", 11),
    },
}

sidebar_item_active_style = {
    **sidebar_item_style,
    "background": rx.color("accent", 3),
    "color": rx.color("accent", 11),
    "font_weight": "600",
}

# 导航栏样式
navbar_style = {
    "position": "fixed",
    "top": "0",
    "left": SIZES["sidebar_width"],
    "right": "0",
    "height": SIZES["navbar_height"],
    "background": rx.color("gray", 1),
    "border_bottom": f"1px solid {rx.color('gray', 4)}",
    "padding": "0 24px",
    "display": "flex",
    "align_items": "center",
    "justify_content": "space-between",
    "z_index": "50",
}

# 主内容区域样式
main_content_style = {
    "margin_left": SIZES["sidebar_width"],
    "margin_top": SIZES["navbar_height"],
    "padding": "24px",
    "min_height": f"calc(100vh - {SIZES['navbar_height']})",
    "background": rx.color("gray", 2),
}

# 页面容器样式
page_container_style = {
    "width": "100%",
    "max_width": "1400px",
    "margin": "0 auto",
}

# 徽章样式
badge_style = {
    "padding": "4px 12px",
    "border_radius": "20px",
    "font_size": "12px",
    "font_weight": "600",
}

badge_success_style = {
    **badge_style,
    "background": rx.color("green", 3),
    "color": rx.color("green", 11),
}

badge_warning_style = {
    **badge_style,
    "background": rx.color("orange", 3),
    "color": rx.color("orange", 11),
}

badge_danger_style = {
    **badge_style,
    "background": rx.color("red", 3),
    "color": rx.color("red", 11),
}

# 图标按钮样式
icon_button_style = {
    "width": "40px",
    "height": "40px",
    "border_radius": "50%",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "cursor": "pointer",
    "transition": "all 0.2s ease",
    "background": "transparent",
    "_hover": {
        "background": rx.color("gray", 3),
    },
}
