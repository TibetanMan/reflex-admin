"""关于页面"""

import reflex as rx
from ..templates.template import template, page_header
from ..styles import card_style, COLORS


def feature_card(icon: str, title: str, description: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon(icon, size=28, color="white"),
                padding="16px",
                border_radius="12px",
                background=f"linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']})",
            ),
            rx.heading(title, size="4", font_weight="600"),
            rx.text(description, color="var(--gray-9)", font_size="14px", text_align="center"),
            spacing="3",
            align="center",
        ),
        **card_style,
        text_align="center",
    )


@template
def about() -> rx.Component:
    return rx.vstack(
        page_header(title="关于系统", subtitle="了解更多关于 Admin Pro 管理系统的信息"),
        rx.box(
            rx.vstack(
                rx.heading("Admin Pro 管理系统", size="6"),
                rx.text("基于 Reflex 框架构建的现代化后台管理系统", color="var(--gray-9)"),
                rx.divider(margin="16px 0"),
                rx.text("版本: v1.0.0 | 作者: Your Name | 许可证: MIT", font_size="14px"),
                spacing="3",
                align="start",
                width="100%",
            ),
            **card_style,
        ),
        rx.grid(
            feature_card("layout-dashboard", "响应式布局", "完美适配各种设备"),
            feature_card("palette", "主题定制", "支持明暗主题切换"),
            feature_card("shield-check", "权限管理", "灵活的权限控制"),
            feature_card("zap", "高性能", "优化的交互体验"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        width="100%",
        spacing="6",
        align="start",
    )
