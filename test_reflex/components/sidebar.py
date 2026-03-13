"""Sidebar component."""

import reflex as rx

from ..state import AuthState
from ..styles import (
    COLORS,
    SIZES,
    sidebar_item_active_style,
    sidebar_item_style,
    sidebar_style,
)


class SidebarState(rx.State):
    """Sidebar local state."""

    is_collapsed: bool = False

    def toggle_sidebar(self):
        self.is_collapsed = not self.is_collapsed


def sidebar_logo() -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("bot", size=24, color="white"),
            style={
                "background": f"linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']})",
                "padding": "8px",
                "border_radius": "10px",
            },
        ),
        rx.text(
            "Bot Admin",
            font_size="18px",
            font_weight="700",
            background=f"linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']})",
            background_clip="text",
            style={"-webkit-background-clip": "text", "-webkit-text-fill-color": "transparent"},
        ),
        spacing="2",
        align="center",
        padding="4px 0",
        margin_bottom="12px",
    )


def sidebar_item_dynamic(icon: str, label: str, href: str) -> rx.Component:
    is_active = rx.cond(
        href == "/",
        rx.State.router.page.path == "/",
        rx.State.router.page.path.startswith(href),
    )

    return rx.link(
        rx.hstack(
            rx.icon(
                icon,
                size=18,
                color=rx.cond(is_active, rx.color("accent", 11), rx.color("gray", 11)),
            ),
            rx.text(label, font_size="13px", font_weight=rx.cond(is_active, "600", "400")),
            padding="8px 12px",
            border_radius="6px",
            width="100%",
            cursor="pointer",
            transition="all 0.2s ease",
            background=rx.cond(is_active, rx.color("accent", 3), "transparent"),
            color=rx.cond(is_active, rx.color("accent", 11), rx.color("gray", 11)),
            _hover={
                "background": rx.cond(is_active, rx.color("accent", 4), rx.color("gray", 3)),
                "color": rx.color("accent", 11),
            },
        ),
        href=href,
        width="100%",
        style={"text_decoration": "none"},
    )


def sidebar_section(title: str, items: list[rx.Component]) -> rx.Component:
    return rx.vstack(
        rx.text(
            title,
            font_size="10px",
            font_weight="600",
            color=rx.color("gray", 9),
            text_transform="uppercase",
            letter_spacing="0.5px",
            padding="4px 12px",
        ),
        *items,
        width="100%",
        spacing="0",
        align="start",
    )


def sidebar() -> rx.Component:
    core_menu = [
        sidebar_item_dynamic("layout-dashboard", "仪表盘", "/"),
        sidebar_item_dynamic("bot", "Bot 管理", "/bots"),
        sidebar_item_dynamic("package", "库存管理", "/inventory"),
        sidebar_item_dynamic("shopping-cart", "订单管理", "/orders"),
        rx.cond(
            AuthState.is_super_admin,
            sidebar_item_dynamic("send", "消息推送", "/push"),
        ),
    ]

    user_finance_menu = [
        sidebar_item_dynamic("users", "用户管理", "/users"),
        sidebar_item_dynamic("wallet", "财务中心", "/finance"),
    ]

    agent_menu = [
        sidebar_item_dynamic("user-cog", "代理管理", "/agents"),
        sidebar_item_dynamic("store", "商家管理", "/merchants"),
    ]

    system_menu = [
        sidebar_item_dynamic("settings", "系统设置", "/settings"),
        sidebar_item_dynamic("info", "关于系统", "/about"),
    ]

    return rx.box(
        rx.vstack(
            sidebar_logo(),
            sidebar_section("核心功能", core_menu),
            rx.divider(margin="8px 0", opacity="0.5"),
            sidebar_section("用户与财务", user_finance_menu),
            rx.divider(margin="8px 0", opacity="0.5"),
            rx.cond(
                AuthState.is_super_admin,
                rx.fragment(
                    sidebar_section("代理与商家", agent_menu),
                    rx.divider(margin="8px 0", opacity="0.5"),
                ),
            ),
            sidebar_section("系统", system_menu),
            rx.spacer(),
            rx.hstack(
                rx.hstack(
                    rx.avatar(fallback=AuthState.user_name[:1], size="1", radius="full"),
                    rx.vstack(
                        rx.text(
                            AuthState.user_name,
                            font_size="12px",
                            font_weight="600",
                            line_height="1.2",
                        ),
                        rx.text(
                            AuthState.role_display,
                            font_size="10px",
                            color=rx.color("gray", 9),
                            line_height="1.2",
                        ),
                        spacing="0",
                        align="start",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("log-out", size=14),
                    size="1",
                    variant="ghost",
                    color_scheme="red",
                    cursor="pointer",
                    on_click=AuthState.handle_logout,
                ),
                width="100%",
                padding="10px 12px",
                background=rx.color("gray", 2),
                border_radius="8px",
                align="center",
            ),
            rx.text(
                "v1.0 · 2026",
                font_size="10px",
                color=rx.color("gray", 8),
                text_align="center",
                width="100%",
                padding="6px 0",
            ),
            width="100%",
            height="100%",
            spacing="1",
            align="start",
        ),
        position="fixed",
        left="0",
        top="0",
        height="100vh",
        width=SIZES["sidebar_width"],
        background=rx.color("gray", 1),
        border_right=f"1px solid {rx.color('gray', 4)}",
        padding="16px 12px",
        z_index="100",
        overflow_y="auto",
    )


def sidebar_item(icon: str, label: str, href: str, is_active: bool = False) -> rx.Component:
    """Backward-compatible static sidebar item API."""
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(label, font_size="14px"),
            style=sidebar_item_active_style if is_active else sidebar_item_style,
            width="100%",
        ),
        href=href,
        width="100%",
        style={"text_decoration": "none"},
    )
